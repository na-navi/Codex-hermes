# /hermes

Delegate the user's task to Hermes CLI, then review and improve the answer before responding.

## Arguments

- `message`: task to send to Hermes. Supports optional leading flags:
  - `-m <model>`: Hermes model name. Default: cached model, then `grok-4.3`.
  - `-p <provider>`: Hermes provider name.
  - `--raw`: return the Hermes answer after review without applying changes.

## Workflow

1. Treat `$ARGUMENTS` as the complete task text. If it is empty, ask the user for the task.
2. Run `scripts/invoke-hermes.ps1 -Message "$ARGUMENTS"` from this repository root. Use PowerShell on Windows.
3. Read the script output:
   - `SESSION_ID=<id>` gives the Hermes conversation to resume.
   - `MODEL=<model>` and `PROVIDER=<provider>` show the resolved target.
   - Everything after `RESPONSE_BEGIN` is the Hermes answer.
4. Review the Hermes answer yourself before showing it to the user:
   - Check factual claims against local repo context or current authoritative sources when needed.
   - For code or commands, inspect affected files and run focused validation when feasible.
   - Do not blindly trust Hermes output.
5. If you find a concrete issue, send feedback back to Hermes with:

   ```powershell
   scripts/invoke-hermes.ps1 -Resume <SESSION_ID> -Message "<specific review feedback>" -Model <MODEL>
   ```

   Include `-Provider <PROVIDER>` when a provider was used.
6. Repeat review feedback at most three rounds. Stop earlier when the answer is correct enough to use.
7. Apply the corrected result or synthesize the final answer for the user. Mention Hermes only when it materially affects the outcome or when review could not resolve a problem.

## Review Feedback Rules

- Feedback must be specific: cite the file, command, failing assumption, or missing requirement.
- Do not use Hermes for a new unrelated question inside the same `/hermes` run.
- If Hermes remains wrong after three rounds, report the unresolved issue and your own best conclusion.
- If local validation cannot be run, say what was not verified.
