# FinTrace — Four-person project demonstration

**Target duration: 9 minutes 20 seconds.** Allow natural pauses and clicks. Aim for 110–125 spoken words per minute; the screen actions use the remaining time. Speaker labels are placeholders: replace them with your names. Read only the quoted dialogue aloud.

## Roles and timing

| Time | Presenter | Focus | Screen |
| --- | --- | --- | --- |
| 0:00–2:15 | Person 1 | Problem, scope and overview | Team introduction → Overview |
| 2:15–4:35 | Person 2 | Alert evidence and explainable priority | Alert review → Evidence → Priority ledger |
| 4:35–6:55 | Person 3 | Account investigation and connected transfers | Account evidence → Network explorer |
| 6:55–9:20 | Person 4 | Human review, engineering checks and conclusion | Review & audit → test results → Overview |

## Before recording — not spoken

- Start the app using the setup in the [dashboard guide](features/dashboard/README.md). Use a prepared analysis snapshot with both rule and graph outputs already imported. Do not run the full data preparation during the video.
- Use a **disposable demo copy** of the alert database for the review action. Set `FINTRACE_ALERT_DATABASE` to that copy and `FINTRACE_PROCESSED_ROOT` to the prepared processed-data directory before launching the app. Do not submit practice actions against the original investigation store.
- Rehearse the whole route once. Pick an account that has a readable finding **and appears in the linked graph window**. Note its exact bank/account pair, a related alert, and a finding that produces visible highlighted edges.
- Choose an **open** alert so the demonstrated transition is Open → In review. Use an honest demo reviewer identifier, such as `demo-presenter-4`.
- Keep the same snapshot selected throughout. Copy the exact account identifier between screens; the pages do not automatically share the selection.
- Have a terminal ready with a fresh successful `python -m pytest -q` run. Show the actual result, not a typed or edited test count.
- Record at a readable browser zoom. Hide notifications and unrelated tabs. Keep a backup recording of your own successful demo; label it “recorded demonstration” if you use it.
- **Do not memorize counts.** Point to the numbers in your selected snapshot. This script deliberately avoids claiming a detection accuracy, processing speed or live bank connection.

---

## Person 1 — Why we built FinTrace

### 0:00–0:25 | Team on camera

**SHOW:** All four presenters, with the project name visible. Then switch to screen sharing.

**SAY:**

> “Hi, we are the team behind FinTrace. Our project helps a reviewer look through money-transfer patterns and understand why an account needs a closer look. Today, we will show a complete review journey: starting with the overview, checking an alert, following the transfers, and recording a human decision.”

### 0:25–1:10 | Explain the problem

**SHOW:** **Overview**. Keep the sidebar and the “IBM SYNTHETIC DATA” notice visible. Point to the selected snapshot.

**SAY:**

> “One unusual payment does not tell the whole story. The useful clue may be several payments arriving at one account, money moving onward quickly, or transfers passing through a chain of accounts. Checking all of that by hand is difficult.
>
> FinTrace brings those clues together. We use IBM’s synthetic banking dataset. These are made-up transactions for research, not real customer bank records. The app works with a prepared snapshot, not a live banking feed. The snapshot also has a time limit, so the analysis uses only transactions before that point.”

### 1:10–2:15 | Show the overview

**SHOW:** Point to **Accounts for review**, **Review alerts**, **Evidence findings**, and **Open / in review**. Scroll to **Priority distribution**, **Patterns in the queue**, and **Start with these accounts**. Briefly expand **Analysis coverage and limitations**.

**SAY:**

> “These cards summarize the selected analysis. We can see how many accounts need review, how many alerts were created, and how many supporting findings we have. An alert is a prompt to investigate. It is not proof of wrongdoing.
>
> Below that, the chart groups accounts by review priority. The table shows which kinds of patterns are in the queue. We use clear rules and graph checks, not machine learning. For example, we can look for many senders paying one account, or one account paying many recipients.
>
> We also show the limits of the analysis here. If a check could not run, or a search was incomplete, we do not present that as a clean result. Next, [Person 2’s name] will open an alert and show the evidence behind it.”

---

## Person 2 — Why was this alert raised?

### 2:15–2:55 | Filter the review queue

**SHOW:** Click **Alert review**. Show the queue first. Use **Search bank, account or alert ID** to find the rehearsed account. Demonstrate one filter, such as **Evidence family**, then clear it if necessary. Select the rehearsed alert under **Inspect an alert**.

**SAY:**

> “This is the review queue. Instead of reading every transfer in order, a reviewer can search for a bank and account, or filter by status, pattern, priority and currency. These filters help us reach the item we want to investigate.
>
> I have selected an example we checked before recording. We will follow this same account through the next screens. The table tells us the pattern, the current status and the number of referenced transfers.”

### 2:55–3:55 | Inspect evidence, not just a warning

**SHOW:** Open **Evidence** and expand a finding. Point to its explanation, time window, transaction references, **Observed measurements**, **Policy thresholds**, and limitations. If the finding is long, show just one clear measurement and its matching threshold. Briefly point to **Download finding evidence (JSON)**; downloading is optional.

**SAY:**

> “Here is what makes the alert explainable. We do not only show a warning. We show the pattern that was found, the time period, and the transaction references supporting it.
>
> On one side are the observed measurements. On the other are the rules used for the check. We can compare what happened with the condition that triggered the finding. The exact values depend on the example selected here.
>
> We can also download this finding as a structured evidence file. That is a copy for inspection, not an automatically submitted report. The limitations stay visible too. A pattern like this can have a legitimate explanation, so a person still needs to review it.”

### 3:55–4:35 | Explain the score

**SHOW:** Click **Priority ledger**. Point to the score and the family/points table. Show **Suppressed correlations** if nonzero; do not invent an example if it is zero.

**SAY:**

> “The priority ledger explains the score. Different types of evidence contribute fixed points. Related findings are grouped so we do not keep adding points for the same kind of clue. The score is capped at one hundred.
>
> A score of eighty would mean ‘review this sooner.’ It would not mean an eighty percent chance of crime. We can see where the points came from instead of trusting a hidden calculation. Now, [Person 3’s name] will follow the account and its connections.”

---

## Person 3 — Follow the account and the transfers

### 4:35–5:35 | Account evidence

**SHOW:** Click **Account evidence**. Select the same exact bank/account pair. Show **Priority**, **Subject findings**, and **Linked alerts**. Open **Observed transfers** and click **Load graph-window transfers**. Point to the per-currency totals and transfer table.

**SAY:**

> “This page brings the selected account’s evidence together. We can see its review priority, findings and linked alerts without jumping between unrelated records.
>
> In Observed transfers, we load the transfers from the linked graph window. The table shows when each transfer happened, who sent it, who received it, and the amounts on each side.
>
> We keep currencies separate. We do not add dollars and another currency into one misleading total. We also do not call these totals an account balance. This is a view of observed transfers in one analysis window, not the account’s complete banking history.
>
> Notice that customer profile details are marked unavailable. The source does not provide verified customer information, so we do not make it up.”

### 5:35–6:55 | Interactive network exploration

**SHOW:** Click **Network explorer**. Select the same **Seed account**. Choose the rehearsed **Highlight finding**. Hover a transfer, drag a node, change **Direction**, then change **Neighbourhood hops** from 1 to 2. Keep **Account display limit** small enough to remain readable. Open **Displayed transfers — precise amounts and source references**. Point to any partial-view warning.

**SAY:**

> “The network view makes relationships easier to follow. Each dot represents an account. Each arrow represents a transfer. We can look at incoming transfers, outgoing transfers, or both, and expand outward from the selected account.
>
> When I select a finding, the orange edges identify its supporting transfers. Hovering shows details, and the table below keeps the exact transaction references available.
>
> A connection on a graph is not enough to prove that money followed a route. Our temporal graph checks also look at the order of the transfers. A later payment cannot explain an earlier one, and equal timestamps do not establish an order.
>
> We limit how much of the graph is searched and displayed. If the view is partial, the screen says so. That keeps the display readable without pretending we have shown every connection. Next, [Person 4’s name] will show how the human review is saved.”

---

## Person 4 — Record a decision and explain the engineering

### 6:55–7:55 | Audited human review

**SHOW:** Return to **Alert review**, reselect the rehearsed alert and open **Review & audit**. On the **disposable demo database only**, choose **In review**, enter the reviewer and the reason below, then click **Save audited review** once. Show the success message and new audit row. Refresh once to show the saved state remains.

**Suggested reason:** `Demo review started. Checking the linked transfers; no conclusion about wrongdoing has been reached.`

**SAY:**

> “The final decision stays with the reviewer. In this demo copy, I will move this open alert to In review. I enter who is reviewing it and why, then save the action.
>
> The history now records the person, time, action and reason. Previous events remain in the history rather than being overwritten. Refreshing the page keeps the saved state; it does not submit the action again.
>
> This is an alert review workflow. It is not a complete case-management system. FinTrace does not freeze accounts, contact a bank, or file a regulatory report.”

### 7:55–8:45 | Show what supports the demo

**SHOW:** Switch to the prepared terminal showing the actual successful test run. Then show the [architecture document](architecture.md), or a simple slide with `Prepare data → Find patterns → Assign priority → Review evidence`.

**SAY:**

> “Behind the interface, we separated data preparation, pattern checks, priority scoring and review screens. During preparation, we preserve source references and check the data before using it. Invalid financial rows go into a separate list for inspection.
>
> The dataset also contains labels saying which synthetic transfers were marked as laundering. Those labels are stored separately and are not used by our detectors or scores. That prevents the system from simply reading the answer.
>
> Here are the results of our automated checks. They cover things like exact amounts, time limits, evidence references, saved review actions and interface behaviour. Passing tests does not prove detection accuracy, but it helps us check that the implemented behaviour stays consistent.”

### 8:45–9:20 | Honest scope and closing

**SHOW:** Return to **Overview**. Finish with all four presenters on camera if practical.

**SAY:**

> “What we have built is a working path from prepared synthetic transfers to explainable findings, review priorities, account and network investigation, and a saved human review history.
>
> Full case management, general reports, replay and benchmark evaluation are future work. We are not claiming an accuracy percentage today.
>
> Our main aim is simple: do not just flag a pattern. Show the evidence, explain the priority, and let a person make an informed decision. That is FinTrace. Thank you.”

---

## Recording adjustments

- **To fit about 7 minutes:** shorten the introduction; show one evidence measurement; omit the download cue; keep the network view at one hop; show the test result for ten seconds. Keep the synthetic-data notice, score disclaimer and future-work statement.
- **To reach about 10 minutes:** let the network interaction breathe, compare one incoming and one outgoing transfer, and show one audit event in detail. Do not fill time with unsupported accuracy or production-readiness claims.
- **If no graph is linked:** fix the demo setup before recording. Do not narrate a missing graph as a working demonstration. A clearly labelled earlier recording of your own working graph is an acceptable backup.
- **If saving review fails:** do not keep clicking. Show the error, refresh, inspect the current state and retry only after checking whether the action was saved. Use the backup recording if needed.
- **Language guardrails:** say “pattern for review,” not “caught a criminal”; say “review priority,” not “fraud probability”; say “observed transfers,” not “full account balance.”
