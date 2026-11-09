# WHEN Resource Hub, weekly updates

## What updates by itself, every Monday

| What | How |
|------|-----|
| Deadline status | Each fellowship in `curated.json` has a `deadline` (YYYY-MM-DD). The site shows "Open now", "Closing soon, N days left", or, once the date has passed, "Next:" followed by the usual period (`window`). |
| Order | Closing-soon fellowships come first, then open ones by date. |
| New rounds | The bot reads the official page of every fellowship. If the part of the page about dates and deadlines changes, it opens a GitHub Issue listing exactly which calls to check. GitHub emails you about every new Issue. |
| Broken links | Listed in the same Issue. |
| "Deadlines checked" date | Shown on the site after every run, and "Checked" on each entry. |
| Deadline calendar | `deadlines.ics` is rebuilt every week. Anyone can subscribe to it in Outlook or Google Calendar and receive a reminder two weeks before each deadline. |
| Monthly email | On the first Monday of each month the bot opens an Issue with a ready-to-send email (`DIGEST.md`) listing the deadlines of the next two months. Copy it to the mailing list. |

## What you do (about 10 minutes every one or two weeks)

1. Open the Issue the bot created (or the file Claude sends you every two weeks).
2. For each fellowship with a new round, edit `curated.json` on GitHub
   (pencil icon) and set the new `deadline`, for example `"deadline": "2027-02-26"`.
3. Commit. The site updates at the next run, or straight away if you go to
   Actions > Update WHEN resources > Run workflow.
4. Close the Issue.

## Adding a fellowship

Copy one block in `curated.json` and change the fields:

```json
{
  "t": "Name of the fellowship",
  "u": "https://official-page",
  "c": "Fellowships and awards",
  "s": "Early career",
  "scope": "UK",
  "cost": "Free",
  "window": "February",
  "deadline": "",
  "desc": "One sentence on what it offers and who it is for.",
  "tags": ["fellowship", "women"],
  "ff": ["part-time", "career-break", "caring-costs"],
  "source": "curated",
  "status": "published"
}
```

Leave `deadline` empty if the next date is not announced yet. The site then shows `window`.

`s` (stage) is one of: `Before PhD`, `PhD`, `Early career`, `Mid-career`, `Returners`, `All stages`.

`who` is optional: one sentence on who can apply (years since PhD, nationality, mobility rules), taken from the official rules.

`ff` (parents and carers) is optional. Use only what the official rules confirm:
`part-time` (can be held part-time), `career-break` (eligibility extended after
parental leave, illness or caring), `caring-costs` (funds can cover childcare or caring costs).

Other optional fields, all from the official rules:

- `c` can also be `Help with costs` (childcare, caring, travel or hardship grants) or `Part-time and flexible work`.
- `amount`: short text such as `Up to £250`. It appears in bold under the title.
- `min_years` and `max_years`: the time limit after the PhD, as numbers. The card shows, for example, "Up to 4 years after PhD".
- `break_rule`: one sentence on how parental leave, caring or illness extend the limit. It appears under Info.
- `part_time`: `true` if the fellowship can be held part-time. The card then shows "Part-time possible".
- `country`: for European programmes, for example `Germany`.
- `note`: anything else useful, for example a confirmed closing date.

## Sharing the work

So that the hub does not depend on one person, add at least one more
administrator (Settings > Collaborators), for example someone from SBBS WHEN.
Everything this file describes can be done from the GitHub website.

## One-time setup

1. Upload all the files of this folder to the repository (keep the `.github/workflows` folder).
2. Settings > Actions > General > Workflow permissions > "Read and write permissions".
3. Actions > Update WHEN resources > Run workflow, once, to test it.
   The first run only records the pages. From the second run, changes are reported.

## Suggestions from the community

People can suggest a resource from the form on the site (it opens an email to the
mailing list) or, if they have a GitHub account, from Issues > New issue >
"Suggest a resource". Both end up with the WHEN team.

## Measuring use and showing the visitor count (no cookies)

1. Create a free account at https://www.goatcounter.com, for example with the code `when-hub`.
2. In `index.html`, search for `const GOATCOUNTER=''` and write the code between the quotes: `const GOATCOUNTER='when-hub'`.
3. In GoatCounter, Settings, tick "Allow adding visitor counts on your website".
   The site then shows "N visits since launch" in the footer and under "Did the hub help you?".
4. The GoatCounter dashboard also shows, without cookies or personal data:
   which resources people open (`open/...`), which ones they read more about (`more/...`)
   and which deadlines they add to their calendar (`calendar/...`).
5. "Did the hub help you?" counts each click as `help/found`, `help/applied` or `help/won`.
   The page shows these totals publicly ("N people", "N positive experiences shared so far").
   Each browser can give each answer once. Mistake reports are counted as `mistake/...`.

## Monthly selection for the mailing list

On the first Monday of each month the robot opens a GitHub Issue called "Monthly selection for the mailing list".
It contains the text version and a link to the email version, `DIGEST.html`, on the site.

1. Open the link, select all (Ctrl+A or Cmd+A), copy and paste into a new email in Outlook.
2. Use the subject written at the top of the page.
3. Read it once and send it.

Each issue includes the deadlines in the next ten weeks, one resource for each of five themes (it rotates every month),
the resources added in the last month (field `added`) and the next three WHEN events from `events.json`.
To prepare it on another day, press "Run workflow" in the Actions tab.

## Bluesky posts every Monday

After the weekly update, `social_bot.py` posts the Resource of the Week (the same one the site shows) and up to two
deadlines closing in the next 14 days, each with an image in the hub's style. It never posts the same deadline twice.

One-time setup, about five minutes:

1. Log in to the WHEN Bluesky account, then Settings, Privacy and security, App passwords, Add app password.
   Call it `resource-hub` and copy the password (it looks like `abcd-efgh-ijkl-mnop`).
2. In GitHub, open the repository, Settings, Secrets and variables, Actions, New repository secret. Add two secrets:
   - `BSKY_HANDLE`: the account name, for example `when-qmul.bsky.social`
   - `BSKY_APP_PASSWORD`: the app password from step 1
3. In the Actions tab, press "Run workflow" once to check that the post appears.

To stop the posts, delete the two secrets. Without them the bot only prepares the drafts.

## LinkedIn post, by email

Every Monday the robot also opens an Issue called "Posts for this week", with the same text and image ready for LinkedIn.
GitHub emails every new Issue to people who watch the repository (Watch, All activity), so it arrives in your inbox.
Copy the text, save the image and post it on the WHEN LinkedIn page.

## Messages from visitors, sent directly (Formspree)

"Report a mistake" and "Suggest a resource" send their messages from the page itself. The answers to "Did the hub help you?" are counted by GoatCounter and need no form service.

1. Create a free account at formspree.io with the WHEN email address and make a new form.
2. Copy the form address, which looks like `https://formspree.io/f/abcdwxyz`.
3. In `index.html`, paste it in `const FORM_ENDPOINT='';` and upload the file.

From then on every message arrives in the WHEN inbox, and visitors see "Your message has been sent". The free plan includes 50 messages a month.
Until the address is set, the forms open the visitor's email app as before.

## Handover, in one minute

- The site is `index.html`. The list is `curated.json`. Everything else is automatic.
- Every Monday the bot updates deadlines and the calendar, and opens Issues when something needs a human.
- The first Monday of each month it opens an Issue with the email for the mailing list.
- At least two people should be administrators of the repository.
