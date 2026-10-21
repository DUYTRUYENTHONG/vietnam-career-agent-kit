# Third-party notices

Original toolkit code is licensed under LICENSE (MIT). No code, templates, biographies, candidate files or settings from the four reference repositories are vendored. Their ideas informed this original implementation. A public repository is not automatically reusable without its license.

| Reference | Reviewed commit | Root license and scope |
|---|---|---|
| [job-apply-assistant](https://github.com/saizongmm/job-apply-assistant) | fbce87dc99bc1ac09df4148b9677d5db9fb63d0e | MIT; no copied code |
| [career-ops](https://github.com/career-ops-hq/career-ops) | c87e0f05a5bf3b0e7bff1f6c87fd0865191e7da7 | MIT; no copied code/installers/browser orchestration |
| [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) | 4339153f8f5e4bb69eaee2a50af713815409e8e7 | MIT; no copied candidates/market defaults/settings |
| [claude-resume-kit](https://github.com/ARPeeketi/claude-resume-kit) | 69930e9de21d5595f9b8c9427adc9c51a9fcbc0e | MIT root; cv.cls/resume.cls have Trey Hunner/LaTeXTemplates notices. Neither class is copied. |

MIT source reuse would require preserving the upstream copyright/license notices; class-specific attribution also survives if those assets are adopted later. Re-review every changed dependency/reference revision. Current core/test/hook/demo dependency lock has no third-party packages. Optional document libraries have separate licenses and are not installed automatically.

See docs/REFERENCE_REVIEW.md for exact inspected files, evidence hashes, useful ideas and limitations. Source audits are static review, not execution permission, full transitive security analysis or verification of every upstream claim.
