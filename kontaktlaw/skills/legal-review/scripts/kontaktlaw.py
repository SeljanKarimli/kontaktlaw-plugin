from kontaktlaw_core.cli import main
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    main()
