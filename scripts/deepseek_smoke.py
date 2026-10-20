"""Manuellt rökprov mot DeepSeek. Ingår inte i make check.

Kör endast vid behov; varje anrop är ett betalt API-anrop.
Läser DEEPSEEK_API_KEY och DEEPSEEK_MODEL via load_deepseek().
Skriver aldrig ut nyckeln eller hela svaret.
"""
import argparse
import sys

from infrastructure.deepseek import DeepSeekClient, DeepSeekError
from infrastructure.settings import load_deepseek


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rökprov mot DeepSeek")
    parser.add_argument("--prompt", default="Svara bara med ordet OK.",
                        help="Fråga till modellen (kort)")
    parser.add_argument("--max-tokens", type=int, default=20)
    args = parser.parse_args(argv)

    try:
        settings = load_deepseek()
    except ValueError as exc:
        print(f"Konfigurationsfel: {exc}", file=sys.stderr)
        return 2

    client = DeepSeekClient(settings, max_retries=0)
    print(f"modell: {settings.model}")
    try:
        svar = client.chat([{"role": "user", "content": args.prompt}],
                           max_tokens=args.max_tokens)
    except DeepSeekError as exc:
        print(f"Anrop misslyckades: {exc}", file=sys.stderr)
        return 1

    # Skriv bara ut en trunkerad rad – aldrig hela payloaden
    print(f"svar (max 200 tecken): {svar[:200]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
