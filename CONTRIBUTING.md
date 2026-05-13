# Contributing

Thanks for helping improve BotFucker.

This project works best when contributions are practical, easy to review, and respectful of user privacy.

## Good Contributions

- Add cold outreach phrases that are common and specific.
- Reduce false positives for real customers, coworkers, support messages, invoices, and personal mail.
- Improve setup instructions for Gmail, Outlook, Yahoo, Proton Mail bridges, or other providers.
- Add tests using synthetic or anonymized email samples.
- Suggest lightweight NLP approaches that do not require a large service dependency.
- Improve safety features such as dry-run output, logging, or whitelist handling.

## Before Opening A Pull Request

Run:

```bash
python -m py_compile outreach_filter.py
```

If you add tests later, include the test command in your pull request description.

## Privacy Rules

Do not include:

- real email messages
- real sender lists
- real blacklist data
- passwords
- tokens
- API keys
- private CRM data

Use fake examples like `sales.example.com` or `person@example.com`.

## Filter Rule Guidelines

Prefer patterns that are:

- specific
- explainable
- easy to review
- unlikely to catch normal human email

Avoid rules that target protected classes, personal traits, or anything unrelated to message behavior.

## Pull Request Checklist

- The change has a clear purpose.
- The script still passes `python -m py_compile outreach_filter.py`.
- No secrets or private email data are included.
- README or comments are updated if behavior changed.
