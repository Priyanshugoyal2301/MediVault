# Frontend verification handoff

For the owner's AntiGravity session. Codex checks APIs, database behavior and security;
browser verification is delegated by the owner, not performed in this session.

Run against http://127.0.0.1:3000 with synthetic accounts and documents only.
Do not send medical documents, `.env.local`, cookies, invitation tokens or recovery
codes to external services. Do not change code as part of this inspection; report
reproduction steps, expected/actual behavior and screenshots with secrets obscured.

1. Register two accounts. Check sign-in, sign-out, failed credentials and refresh.
2. Create an adult profile and a child profile. Pending guardian verification must
   remain locked. Switching profiles must never briefly show the previous profile's data.
3. Upload a clear synthetic prescription PNG and a synthetic report PDF. Check queued,
   reading, review and failed states. Compare all extracted text with the original.
   OCR text must not automatically assert a medicine is currently being taken.
4. Download originals, review English/Hindi explanations and inspect historical dates.
   Blank/illegible documents must not display invented information.
5. Create/edit medicines, reactions, visits, appointments, vaccinations, referrals,
   claims and benefits. Check validation, empty states and reload persistence.
6. Invite the second account with documents-only read access. Verify other categories
   are absent, writes are unavailable and revocation removes access after refresh.
7. Enable authenticator MFA with a synthetic account; store recovery codes privately.
   Check login challenge, recovery and disabling MFA. Never include keys in screenshots.
8. Inspect navigation, forms, dialogs, keyboard focus, overflow and touch targets at
   360, 390, 768 and 1440 pixels. Test narrow landscape, long names and large text.
9. Confirm slow/failed API responses show useful errors and do not falsely report saves.
10. Review the consultation summary, print layout and JSON export with restricted access.

Return issues with severity, exact steps, viewport/browser and sanitized evidence.
Browser observations are not a substitute for server authorization tests or a security audit.
