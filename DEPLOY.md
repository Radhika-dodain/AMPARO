# Putting Amparo online

Written for someone who has never deployed anything. Every command is meant to
be copied exactly. If something does not match what this page says, stop and
read the **When it goes wrong** section at the bottom rather than improvising —
almost every failure here has one specific cause.

**Time needed:** about 20 minutes, most of it waiting for the first build.

**What you will end up with:** one web address, something like
`https://amparo.onrender.com`, that opens the whole app on any phone or laptop.

---

## How this works, in one paragraph

There is only one program to deploy. The Python backend serves both the API
*and* the finished web page, so there is no second service, no separate
frontend host, and no cross-origin configuration to get wrong. Two things that
are usually built on the server are instead built on your machine and committed
to the repository: the risk-scored street map, and the frontend. That is why
the server only has to run `pip install` and start.

---

## Step 1 — Put the code on GitHub

### 1a. Make an empty repository

1. Go to **https://github.com/new**
2. **Repository name:** `amparo`
3. Leave it **Public** (Render's free plan can read private repos too, but
   public is simpler and you may want to show it off).
4. **Do not tick** "Add a README", "Add .gitignore", or "Choose a license".
   The project already has all three, and ticking them creates a conflict you
   would then have to untangle.
5. Click **Create repository**.

GitHub now shows you a page of commands. Ignore it — use the ones below, which
are already correct for this project.

### 1b. Push the code

Open a terminal **in the project folder** and run these one at a time.
Replace `YOUR-USERNAME` with your actual GitHub username.

```bash
git remote add origin https://github.com/YOUR-USERNAME/amparo.git
```

```bash
git push -u origin main
```

A window will pop up asking you to sign in to GitHub. Sign in and allow it.

> **If no window appears** and it asks for a password in the terminal instead:
> GitHub stopped accepting account passwords here in 2021. You need a Personal
> Access Token, which is just a long password for tools:
> go to **https://github.com/settings/tokens?type=beta** → *Generate new token*
> → give it a name, set **Repository access** to *Only select repositories* →
> pick `amparo` → under **Repository permissions** set *Contents* to
> **Read and write** → *Generate token*. Copy the token and paste it where the
> terminal asks for a password. (Nothing will appear as you paste. That is
> normal.)

Refresh your GitHub repository page. You should see the files.

---

## Step 2 — Deploy on Render

1. Go to **https://render.com** and click **Get Started** / **Sign in**.
2. Choose **Sign in with GitHub**. This is the easy path — it lets Render see
   your repositories without any further setup.
3. On the dashboard click **Add new +** → **Web Service**.
4. Find `amparo` in the list and click **Connect**.
   - If it is not listed, click **Configure account** and give Render access to
     the repository.
5. Render reads `render.yaml` from the repository and fills everything in
   itself: the name, the Python version, the build command, the start command
   and all the settings. **Change nothing.**
6. Check that **Instance Type** says **Free**.
7. Click **Deploy Web Service**.

Now wait. The first build takes **5–10 minutes**, because it is downloading and
installing the mapping libraries. You will see a log scrolling past. That is
normal and you do not need to read it.

**You are done when** the log ends with something like:

```
[amparo] ready in 0.6s
INFO:     Application startup complete.
==> Your service is live 🎉
```

Your address is at the top of the page. Click it.

---

## Step 3 — Check it actually works

Open your new address and confirm, in this order:

1. **The map draws**, with real Pune streets and coloured shading along them.
2. Click **Demo trip**. Two routes appear — a solid green one and a dashed
   orange one — with numbers underneath.
3. Click **Night** at the top. The colours shift and the tradeoff changes to
   roughly *"80 m further, risk down 43%"*.
4. Open `https://YOUR-ADDRESS/health` in a new tab. It should say
   `"status":"ok"` and `"edges":974`. If the edge count is 0, the map file did
   not ship — see the troubleshooting table.
5. **Open it on your actual phone**, over mobile data, not wifi. This is the
   test that matters, and it is the one people skip.

---

## Step 4 — Every time you change something afterwards

This is the part that trips people up, so it gets its own step.

Because the frontend is built on your machine, **you must rebuild before you
push** or the live site will keep showing the old version while your code looks
correct. Always run these three, in this order:

```bash
cd frontend && npm run check && cd ..
```

```bash
git add -A && git commit -m "describe what you changed"
```

```bash
git push
```

Render notices the push and redeploys on its own, in about two minutes.

`npm run check` runs the linter and then the build. The linter matters: the
build alone will happily bundle a reference to a variable that does not exist
and hand you a blank white page with no error anywhere.

---

## The one thing that will bite you on demo day

**Render's free plan puts your app to sleep after 15 minutes with no visitors.**
Waking it takes **about 50 seconds**, during which whoever opened your link
stares at a blank tab and assumes it is broken.

The fix is not clever, and you should do it anyway:

> **Open your link about five minutes before you present, and leave the tab
> open.** Every visit resets the 15-minute timer, so if you are clicking around
> during your own rehearsal it will stay awake.

If you would rather not rely on remembering: sign up at
**https://uptimerobot.com** (free), add an HTTP monitor pointing at
`https://YOUR-ADDRESS/health` with a 5-minute interval, and it will keep the app
permanently awake by pinging it. Five minutes to set up, and it removes the risk
entirely.

---

## A thing to know about reports

The reports people submit are stored in a file on the server, and Render's free
plan gives each deploy a **fresh, empty filesystem**. So reports vanish when the
app sleeps, restarts, or is redeployed.

Within a single demo this is invisible and everything works: you submit a
report, the map recolours, the route moves. But do not submit reports the night
before and expect to find them the next morning.

If you later want them to persist, the fix is a Render **persistent disk**
(paid, about $1/month) mounted at `backend/data`, or moving the reports to a
hosted database. Neither is worth doing before the hackathon.

---

## When it goes wrong

| What you see | What it actually means | Fix |
|---|---|---|
| Build fails, log mentions `gcc`, `Building wheel`, or `Killed` | The installer is trying to compile numpy or scipy from source because the Python version changed | In Render: **Environment** → check `PYTHON_VERSION` is `3.12.7`. Then **Manual Deploy** → **Clear build cache & deploy** |
| Build succeeds, site shows **"No street map at ..."** | `backend/data/graph_cache.graphml` did not reach GitHub | Run `git ls-files backend/data` locally. If the `.graphml` is missing, run `git add -f backend/data/graph_cache.graphml` then commit and push |
| `/health` says `"edges": 0` | Same as above | Same as above |
| Blank white page, map never appears | A JavaScript error | Press **F12** in the browser, open the **Console** tab, and read the red line. Usually a rebuild was forgotten — run `npm run check` and push |
| Map is blank grey but the panel works | Tile server unreachable | Tick **Quiet map** in the top-right of the map; that uses a different tile provider |
| Site shows an old version of the frontend | You pushed without rebuilding | `cd frontend && npm run check`, then commit and push |
| First visit takes ~50 seconds | The free plan was asleep | Expected. See the demo-day section above |
| `git push` rejected, "failed to push some refs" | Something exists on GitHub that you do not have locally — usually a README added at creation time | `git pull --rebase origin main` then push again |

---

## What is where, if you need to poke at it

| | |
|---|---|
| Render dashboard | https://dashboard.render.com |
| Live logs | Your service → **Logs** (this is where a crash explains itself) |
| Settings and env vars | Your service → **Environment** |
| Force a rebuild | Your service → **Manual Deploy** → *Clear build cache & deploy* |
| Change the demo area | Edit `DEMO_BBOX` in `render.yaml`, then rebuild the map cache locally with `python scripts/build_cache.py` and push. Changing it only on Render will route people around a map that no longer matches |
