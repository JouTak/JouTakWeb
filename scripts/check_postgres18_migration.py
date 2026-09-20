"""Exercise the actual migration on disposable Docker volumes."""

import json
import subprocess
import tempfile
import uuid
from pathlib import Path

import yaml
from migrate_postgres18 import PG16, PG18, migrate, output, sql, wait_ready


def fingerprint(volume):
    return output(
        "run",
        "--rm",
        "--network",
        "none",
        "--mount",
        f"type=volume,source={volume},target=/source,readonly",
        "--entrypoint",
        "sh",
        PG16,
        "-ec",
        "find /source -type f -exec sha256sum {} + | sort",
    )


def main():
    prefix = f"joutak-pg18-test-{uuid.uuid4().hex}"
    source, target = f"{prefix}-source", f"{prefix}-target"
    old, new = f"{prefix}-old", f"{prefix}-new"
    try:
        output("volume", "create", source)
        output(
            "run",
            "-d",
            "--name",
            old,
            "--network",
            "none",
            "--mount",
            f"type=volume,source={source},target=/var/lib/postgresql/data",
            "-e",
            "POSTGRES_USER=joutak",
            "-e",
            "POSTGRES_DB=joutak",
            "-e",
            f"POSTGRES_PASSWORD={uuid.uuid4().hex}",
            PG16,
        )
        wait_ready(old, "joutak", "joutak")
        sql(
            old,
            "joutak",
            "joutak",
            """
CREATE ROLE reader LOGIN PASSWORD 'test-only-password';
CREATE TABLE profiles (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                       name text NOT NULL, settings jsonb);
INSERT INTO profiles (name, settings) VALUES
('Игрок', '{"verified":true}'), ('Second', '{"verified":false}');
GRANT SELECT ON profiles TO reader;
CREATE INDEX profiles_name ON profiles (name);
""",
        )
        sql(old, "joutak", "postgres", 'CREATE DATABASE "extra-db"')
        sql(old, "joutak", "extra-db", "CREATE TABLE extra (value text)")
        password = sql(
            old,
            "joutak",
            "postgres",
            "SELECT rolpassword FROM pg_authid WHERE rolname='reader'",
        )
        with tempfile.TemporaryDirectory() as directory:
            backup = Path(directory) / "backup"
            try:
                migrate(source, target, "joutak", backup)
            except ValueError as error:
                assert "Stop all source" in str(error)
            else:
                raise AssertionError("Migration accepted a running source")
            output("stop", old)
            before = fingerprint(source)
            migrate(source, target, "joutak", backup)
            assert fingerprint(source) == before, "Source was modified"
            assert (
                json.loads((backup / "verified.json").read_text())["target"]
                == target
            )
            output(
                "run",
                "-d",
                "--name",
                new,
                "--network",
                "none",
                "--mount",
                f"type=volume,source={target},target=/var/lib/postgresql",
                PG18,
            )
            wait_ready(new, "joutak", "joutak")
            assert (
                sql(
                    new,
                    "joutak",
                    "joutak",
                    "SELECT name FROM profiles WHERE id=1",
                )
                == "Игрок"
            )
            assert (
                sql(
                    new,
                    "joutak",
                    "joutak",
                    "SELECT settings->>'verified' FROM profiles WHERE id=1",
                )
                == "true"
            )
            assert (
                sql(new, "reader", "joutak", "SELECT count(*) FROM profiles")
                == "2"
            )
            assert (
                sql(
                    new,
                    "joutak",
                    "postgres",
                    "SELECT rolpassword FROM pg_authid WHERE rolname='reader'",
                )
                == password
            )
            assert (
                sql(
                    new,
                    "joutak",
                    "joutak",
                    "INSERT INTO profiles (name) VALUES ('After') "
                    "RETURNING id",
                ).splitlines()[0]
                == "3"
            )
            assert (
                sql(
                    new,
                    "joutak",
                    "postgres",
                    "SELECT count(*) FROM pg_authid "
                    "WHERE rolname LIKE 'migration_%' "
                    "AND (rolcanlogin OR rolcreatedb "
                    "OR rolcreaterole "
                    "OR rolreplication OR rolbypassrls "
                    "OR rolpassword IS NOT NULL)",
                )
                == "0"
            )
            try:
                migrate(source, target, "joutak", Path(directory) / "retry")
            except ValueError as error:
                assert "already exists" in str(error)
            else:
                raise AssertionError("Migration would overwrite a target")
        # Retained PG16 volumes must fail closed with the Compose command.
        config = yaml.safe_load(Path("compose.yaml").read_text())
        guard = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--mount",
                f"type=volume,source={source},target=/var/lib/postgresql,readonly",
                PG18,
                *config["services"]["db"]["command"],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert guard.returncode != 0
        assert "migration required" in guard.stderr
    finally:
        for container in [old, new]:
            subprocess.run(
                ["docker", "rm", "-f", container],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        for volume in [source, target]:
            subprocess.run(
                ["docker", "volume", "rm", volume],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.stderr) from error
