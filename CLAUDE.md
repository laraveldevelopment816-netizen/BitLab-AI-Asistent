# bitlab-ai-asistent

Voice agent on `aiasistent.bitlab.rs` (prod) / staging. The reference deploy on the shared `aiasistent.bitlab.rs` server — its `scripts/deploy.sh` is the inspiration for cm-viewer and the compliance-monitoring `infra-dashboard/compliance-deploy.sh`.

## Server deploy workflow (cross-project rules)

Cross-project rules from `~/.claude/CLAUDE.md` apply. Recap below.

- **Local files = single source of truth.** Server executes what we send; we verify output. If something fails, fix locally, push, redeploy, re-run on server. Never `vim`/`sed`/`tee` hand-written content on the server.
- **One bash command per turn** for SSH/deploy ops; wait for the user's paste-back before sending the next.
- **Per-action approval** for every server change (sudo, systemd, nginx, etc.). Prior approval does NOT carry over.
- **Verify served, not just saved.** After edits confirm change reached running state.

Full detail in `~/.claude/projects/-mnt-c-Users-Kule-Projects-bitlab-ai-asistent/memory/`:
`feedback_finalize_locally_before_server.md`, `feedback_one_command_at_a_time_deploy.md`, `feedback_no_server_changes_without_approval.md`, `feedback_verify_served_not_saved.md`.

## Project-specific

- This repo's `scripts/deploy.sh` is the reference pattern for server deploys across the `bitlab.rs` ecosystem.
- Shared infrastructure (nginx hosts.d include pattern, systemd unit shape, shared/ folder layout) is reused by cm-viewer and the compliance-monitoring family.

## Git

- Never `git commit` without explicit request.
- Conventional Commits with scope.
