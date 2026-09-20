"""Offline PG16 volume -> new PG18 volume; never writes to the source."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

PG16 = (
    "postgres:16-alpine@sha256:"
    "3c5c8892d184f738f4fe282d14ddaa613a38f00f4189d2d94725ebe6f2909ddb"
)
# Follow the repository's pinned target image, including security updates.
TARGET_MANIFEST = Path(__file__).resolve().parents[1] / "compose.yaml"
PG18_MATCH = re.search(
    r"^    image: (postgres:18-alpine@sha256:[a-f0-9]{64})$",
    TARGET_MANIFEST.read_text(),
    re.MULTILINE,
)
if PG18_MATCH is None:
    raise ValueError("compose.yaml must pin a PostgreSQL 18 image digest")
PG18 = PG18_MATCH.group(1)


def docker(*args, **kwargs):
    return subprocess.run(["docker", *args], check=True, **kwargs)  # noqa: S603,S607


def output(*args):
    return docker(*args, capture_output=True, text=True).stdout.strip()


def sql(container, user, database, query):
    return output(
        "exec",
        container,
        "psql",
        "-XAt",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        user,
        "-d",
        database,
        "-c",
        query,
    )


def wait_ready(container, user, database):
    for _ in range(120):
        # initdb temporarily runs a server too: only accept the final PID 1.
        command = output("exec", container, "cat", "/proc/1/comm")
        if command == "postgres":
            try:
                if sql(container, user, database, "SELECT 1") == "1":
                    return
            except subprocess.CalledProcessError:
                pass
        time.sleep(1)
    raise RuntimeError("PostgreSQL did not become ready within 120 seconds")


def inventory(container, user):
    databases = json.loads(
        sql(
            container,
            user,
            "postgres",
            "SELECT json_agg(datname ORDER BY datname) FROM pg_database "
            "WHERE NOT datistemplate AND datallowconn",
        )
    )
    result = {}
    for database in databases:
        # psql generates correctly quoted queries even for unusual names.
        query = r"""
SELECT format('SELECT %L, count(*) FROM %I.%I;',
              schemaname || '.' || tablename, schemaname, tablename)
FROM pg_tables WHERE schemaname NOT LIKE 'pg_%'
AND schemaname <> 'information_schema' ORDER BY schemaname, tablename
\gexec
"""
        result[database] = docker(
            "exec",
            "-i",
            container,
            "psql",
            "-XAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            user,
            "-d",
            database,
            input=query,
            capture_output=True,
            text=True,
        ).stdout.strip()
    return result


def migrate(source, target, user, backup_dir):
    if not all(
        re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]+", name)
        for name in (source, target)
    ):
        raise ValueError("Use Docker named volumes, not host paths")
    output("volume", "inspect", source)
    if target in output("volume", "ls", "--format", "{{.Name}}").splitlines():
        raise ValueError("Target volume already exists; choose a new name")
    if output("ps", "-q", "--filter", f"volume={source}"):
        raise ValueError("Stop all source-volume containers before migration")
    backup_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    scratch = f"joutak-pg-migrate-{uuid.uuid4().hex}"
    old = f"{scratch}-old"
    new = f"{scratch}-new"
    bootstrap = f"migration_{uuid.uuid4().hex}"
    output("volume", "create", scratch)
    created_containers = []
    try:
        # Explicit source inspection above prevents Docker creating a typoed
        # source volume. Copy only a stopped cluster, with a read-only mount.
        output(
            "run",
            "--rm",
            "--network",
            "none",
            "--mount",
            f"type=volume,source={source},target=/source,readonly",
            "--mount",
            f"type=volume,source={scratch},target=/copy",
            "--entrypoint",
            "sh",
            PG16,
            "-ec",
            'test "$(cat /source/PG_VERSION)" = 16; '
            "test ! -f /source/postmaster.pid; "
            "test ! -L /source/pg_wal; cp -a /source/. /copy/",
        )
        output(
            "run",
            "-d",
            "--name",
            old,
            "--network",
            "none",
            "--mount",
            f"type=volume,source={scratch},target=/var/lib/postgresql/data",
            PG16,
            "postgres",
            "-c",
            "listen_addresses=",
        )
        created_containers.append(old)
        wait_ready(old, user, "postgres")
        if (
            sql(
                old,
                user,
                "postgres",
                "SELECT count(*) FROM pg_tablespace "
                "WHERE spcname NOT IN ('pg_default', 'pg_global')",
            )
            != "0"
        ):
            raise ValueError(
                "Custom tablespaces require a dedicated migration"
            )
        before = inventory(old, user)
        dump_path = backup_dir / "cluster.sql"
        with dump_path.open("xb") as dump:
            os.chmod(dump_path, 0o600)
            docker(
                "exec",
                old,
                "pg_dumpall",
                "-U",
                user,
                "--clean",
                "--if-exists",
                "--quote-all-identifiers",
                stdout=dump,
                stderr=subprocess.PIPE,
            )
        output("volume", "create", target)
        output(
            "run",
            "-d",
            "--name",
            new,
            "--network",
            "none",
            "--mount",
            f"type=volume,source={target},target=/var/lib/postgresql",
            "-e",
            f"POSTGRES_USER={bootstrap}",
            "-e",
            f"POSTGRES_DB={bootstrap}",
            "-e",
            f"POSTGRES_PASSWORD={uuid.uuid4().hex}",
            PG18,
            "postgres",
            "-c",
            "listen_addresses=",
        )
        created_containers.append(new)
        wait_ready(new, bootstrap, bootstrap)
        with dump_path.open("rb") as dump:
            docker(
                "exec",
                "-i",
                new,
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                bootstrap,
                "-d",
                bootstrap,
                stdin=dump,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        sql(new, user, "postgres", f'DROP DATABASE "{bootstrap}"')
        # PostgreSQL pins initdb's bootstrap role to system objects, so it
        # must remain a superuser. Disable login/password and optional rights.
        sql(
            new,
            user,
            "postgres",
            f'ALTER ROLE "{bootstrap}" NOLOGIN '
            "NOCREATEDB NOCREATEROLE NOREPLICATION "
            "NOBYPASSRLS PASSWORD NULL",
        )
        after = inventory(new, user)
        if before != after:
            raise RuntimeError("Restored databases/table counts differ")
        output("exec", new, "vacuumdb", "-U", user, "--all", "--analyze")
        report = {
            "source": source,
            "target": target,
            "target_image": PG18,
            "table_counts": after,
        }
        report_path = backup_dir / "verified.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        os.chmod(report_path, 0o600)
        sys.stdout.write(f"Verified PostgreSQL 18 volume: {target}\n")
    finally:
        for container in reversed(created_containers):
            # Stop cleanly before detaching the migrated persistent volume.
            subprocess.run(
                ["docker", "stop", "-t", "60", container],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Retain the target and backup on failure, for investigation.
            subprocess.run(
                ["docker", "rm", "-f", container],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        subprocess.run(
            ["docker", "volume", "rm", scratch],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-volume", required=True)
    parser.add_argument("--target-volume", required=True)
    parser.add_argument("--superuser", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    migrate(
        args.source_volume, args.target_volume, args.superuser, args.backup_dir
    )


if __name__ == "__main__":
    main()
