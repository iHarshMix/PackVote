# AI Assistant Workflow Rules for PackVote

Follow these strict rules during the development of this project:

1. **Preserve Original Documentation:** Never delete or overwrite the original text in the main project plan (`plan and docs/packvote_project_plan...`). If a deviation from the technical design occurs (e.g., adding a new DB column or changing a route), append an implementation note using a blockquote format (e.g., `> **Implementation Update (Date):** [Reason for change]`) next to the relevant section.
2. **Track Progress via Checkboxes:** The Build Order in the project plan uses Markdown checkboxes. Whenever you complete a step, you must update the project plan file by changing the empty checkbox (`- [ ]`) to checked (`- [x]`).
3. **Use Scratchpad Artifacts for Micro-tasks:** Do not clutter the main project plan with granular, day-to-day to-dos. When executing a complex step, generate an internal `task.md` artifact to act as your dynamic checklist and scratchpad, checking off micro-tasks as you go.
4. **Strict Git Flow:** Before starting a new step in the Build Order, branch out from `main` (e.g., `git checkout -b feat/step-X-name`). Once the step is complete and verified, commit the code and merge it back into `main` before proceeding to the next step.
