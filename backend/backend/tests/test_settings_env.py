from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.settings.env import apply_env_file_overrides


class SettingsEnvFileTests(SimpleTestCase):
    def test_apply_env_file_overrides_reads_secret_from_file(self) -> None:
        with NamedTemporaryFile("w", delete=False, encoding="utf-8") as fh:
            fh.write("super-secret-value\n")
            secret_path = fh.name

        self.addCleanup(lambda: Path(secret_path).unlink(missing_ok=True))

        with patch.dict(
            os.environ,
            {
                "DJANGO_SECRET_KEY_FILE": secret_path,
                "DJANGO_SECRET_KEY": "old-value",
            },
            clear=False,
        ):
            apply_env_file_overrides(("DJANGO_SECRET_KEY",))
            self.assertEqual(
                os.environ["DJANGO_SECRET_KEY"],
                "super-secret-value",
            )

    def test_apply_env_file_overrides_raises_on_unreadable_file(
        self,
    ) -> None:
        missing_path = Path(__file__).with_name(
            "does-not-exist-joutak-key.txt"
        )
        with patch.dict(
            os.environ,
            {"DJANGO_SECRET_KEY_FILE": str(missing_path)},
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "DJANGO_SECRET_KEY_FILE",
            ):
                apply_env_file_overrides(("DJANGO_SECRET_KEY",))

    def test_apply_env_file_overrides_keeps_existing_value_without_file(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {"DJANGO_SECRET_KEY": "existing-value"},
            clear=False,
        ):
            apply_env_file_overrides(("DJANGO_SECRET_KEY",))
            self.assertEqual(os.environ["DJANGO_SECRET_KEY"], "existing-value")
