# One-off generator for the static pages (shared header/footer). Output is plain HTML.
import pathlib, html
ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = "https://app.nxtplaylabs.com"
EMAIL = "support@nxtplaylabs.com"

MARK = '''<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true"><rect x="6" y="6" width="20" height="20" rx="2" transform="rotate(45 16 16)" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="16" cy="25.5" r="3.2" fill="var(--bulb)"/><circle cx="16" cy="6.5" r="1.8" fill="currentColor"/><circle cx="6.5" cy="16" r="1.8" fill="currentColor"/><circle cx="25.5" cy="16" r="1.8" fill="currentColor"/></svg>'''

NAV = [("grind-pass.html", "The Grind Pass"), ("about.html", "About"), ("support.html", "Support"), ("contact.html", "Contact")]

def page(slug, title, desc, body):
    nav = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if h == slug else ""}>{t}</a>' for h, t in NAV
    )
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@800;900&family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="index.html" aria-label="NXT Play Labs home">{MARK}<span class="brand-name">NXT Play <span>Labs</span></span></a>
    <nav class="nav" aria-label="Main">{nav}</nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-top">
      <a class="brand" href="index.html" aria-label="NXT Play Labs home">{MARK}<span class="brand-name">NXT Play <span>Labs</span></span></a>
      <nav class="footer-links" aria-label="Footer">
        <a href="grind-pass.html">The Grind Pass</a>
        <a href="about.html">About</a>
        <a href="support.html">Support</a>
        <a href="contact.html">Contact</a>
        <a href="{APP}/privacy">Privacy</a>
        <a href="{APP}/terms">Terms</a>
      </nav>
    </div>
    <p class="footer-small">© <span data-year>2026</span> NXT Play Labs · {EMAIL}</p>
  </div>
</footer>
<script src="site.js"></script>
</body>
</html>
'''

def write(name, title, desc, body):
    (ROOT / name).write_text(page(name, title, desc, body), encoding="utf-8")

# ---------------- Home ----------------
home = f'''
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="label">Sports tech studio</p>
      <h1 class="display">Built for the <em>next play.</em></h1>
      <p class="lede">NXT Play Labs builds software for youth baseball and softball: tools that help players put in the work between practices and help coaches see it.</p>
      <div class="actions">
        <a class="btn" href="grind-pass.html">See The Grind Pass</a>
        <a class="btn secondary" href="contact.html">Bring it to your team</a>
      </div>
    </div>
    <aside class="board" aria-label="Studio at a glance">
      <div class="board-title"><span>Studio board</span><span class="bulbs" aria-hidden="true"><i class="on"></i><i class="on"></i><i></i></span></div>
      <dl>
        <div class="board-row"><dt>At bat</dt><dd>The Grind Pass</dd></div>
        <div class="board-row"><dt>Sports</dt><dd>Baseball · Softball</dd></div>
        <div class="board-row"><dt>Plays on</dt><dd>iPhone · Android · Web</dd></div>
        <div class="board-row"><dt>Players</dt><dd>Ages 13 and up</dd></div>
        <div class="board-row"><dt>On deck</dt><dd class="plain">In the lab</dd></div>
      </dl>
    </aside>
  </div>
</section>

<section class="section" aria-labelledby="build-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">What we build</p>
      <h2 id="build-h" class="display">One product on the field. More in the lab.</h2>
    </div>
    <article class="product">
      <div class="product-copy">
        <p class="label">Now playing</p>
        <h3 class="display product-name">The Grind Pass</h3>
        <p class="muted">A training app for baseball and softball teams. Coaches plan and assign the work. Players complete it, upload proof, and earn XP, streaks and rewards. The whole team sees it happen in the Clubhouse feed.</p>
        <ul class="ticks">
          <li>Daily plans from the coach, on the player's phone</li>
          <li>Photo and video proof the coach reviews</li>
          <li>XP, streaks, levels and rewards that keep players coming back</li>
        </ul>
        <div class="actions"><a class="btn grind" href="grind-pass.html">Explore The Grind Pass</a></div>
      </div>
      <div class="phones" aria-hidden="true">
        <div class="phone"><img src="assets/shots/complete.webp" alt="" width="390" height="844" loading="lazy"></div>
        <div class="phone small"><img src="assets/shots/plan.webp" alt="" width="390" height="844" loading="lazy"></div>
      </div>
    </article>
  </div>
</section>

<section class="section" aria-labelledby="how-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">How we build</p>
      <h2 id="how-h" class="display">Made for the dugout, not the boardroom.</h2>
    </div>
    <div class="grid-3">
      <div class="tile">
        <p class="label">Coaches first</p>
        <h3>Fits how teams already work</h3>
        <p>Coaches assign, players do the work, coaches review it. We build around that loop instead of adding busywork.</p>
      </div>
      <div class="tile">
        <p class="label">Safe by default</p>
        <h3>Built for young athletes</h3>
        <p>Accounts start at 13. Profiles of players under 18 stay private to their team. Anyone can report or block, and coaches can remove posts. No ads, and we never sell data.</p>
      </div>
      <div class="tile">
        <p class="label">Every surface</p>
        <h3>One account, any screen</h3>
        <p>Players train from their phones. Coaches plan from a laptop or the app. Everything stays in sync.</p>
      </div>
    </div>
  </div>
</section>

<section class="band" aria-labelledby="cta-h">
  <div class="wrap">
    <div>
      <p class="label">Coaches and organizations</p>
      <h2 id="cta-h" class="display">Want The Grind Pass for your team?</h2>
    </div>
    <div class="actions">
      <a class="btn" href="contact.html">Talk to us</a>
      <a class="btn secondary" href="support.html">Read the FAQ</a>
    </div>
  </div>
</section>
'''
write("index.html", "NXT Play Labs", "NXT Play Labs is a sports tech studio building software for youth baseball and softball, starting with The Grind Pass.", home)

# ---------------- The Grind Pass ----------------
gp = f'''
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="label">From NXT Play Labs</p>
      <h1 class="display">The <span style="color:var(--grind)">Grind</span> Pass</h1>
      <p class="lede">The work between practices, planned by the coach and done by the player. Every rep earns XP. Every day keeps the streak alive. The team sees it all.</p>
      <div class="actions">
        <a class="btn grind" href="contact.html">Set up your team</a>
        <a class="btn secondary" href="{APP}/login">Sign in</a>
      </div>
    </div>
    <aside class="board" aria-label="A week on The Grind Pass">
      <div class="board-title"><span>This week · Tee work</span><span class="bulbs" aria-hidden="true"><i class="on"></i><i class="on"></i><i class="on"></i></span></div>
      <div class="linescore-wrap">
        <table class="linescore">
          <thead><tr><th scope="col">Day</th><th scope="col">M</th><th scope="col">T</th><th scope="col">W</th><th scope="col">T</th><th scope="col">F</th><th scope="col">S</th><th scope="col">S</th><th scope="col" class="tot">Tot</th></tr></thead>
          <tbody>
            <tr><td>Done</td><td class="hot">✓</td><td class="hot">✓</td><td class="hot">✓</td><td>·</td><td class="hot">✓</td><td>·</td><td>·</td><td class="tot">4</td></tr>
            <tr><td>XP</td><td class="hot">30</td><td class="hot">25</td><td class="hot">40</td><td>·</td><td class="hot">30</td><td>·</td><td>·</td><td class="tot">125</td></tr>
          </tbody>
        </table>
      </div>
      <dl>
        <div class="board-row"><dt>Streak</dt><dd>3 days</dd></div>
        <div class="board-row"><dt>Next drop</dt><dd>Level 8 badge</dd></div>
      </dl>
    </aside>
  </div>
</section>

<section class="section" aria-labelledby="loop-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">The daily loop</p>
      <h2 id="loop-h" class="display">Plan. Train. Prove. Earn. Team.</h2>
      <p class="muted">Every day on The Grind Pass runs the same five steps.</p>
    </div>
    <ol class="loop">
      <li><h3>Plan</h3><p>The coach assigns workouts or a weekly plan from the drill library.</p></li>
      <li><h3>Train</h3><p>Players see today's work on their phone and get a reminder when it's time.</p></li>
      <li><h3>Prove</h3><p>They log it, with a photo or video when the coach asks for proof.</p></li>
      <li><h3>Earn</h3><p>XP, streaks and levels unlock badges and rewards along the season pass.</p></li>
      <li><h3>Team</h3><p>Wins land in the Clubhouse feed, where teammates react and cheer.</p></li>
    </ol>
  </div>
</section>

<section class="section" aria-labelledby="players-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">For players</p>
      <h2 id="players-h" class="display">Your work, on the scoreboard.</h2>
    </div>
    <div class="phone-row">
      <figure><div class="phone"><img src="assets/shots/plan.webp" alt="The Plan screen showing today's workouts and the week strip" width="390" height="844" loading="lazy"></div><figcaption>Today's plan</figcaption></figure>
      <figure><div class="phone"><img src="assets/shots/complete.webp" alt="Workout complete screen showing plus 25 XP and a six-day streak" width="390" height="844" loading="lazy"></div><figcaption>Workout complete</figcaption></figure>
      <figure><div class="phone"><img src="assets/shots/claimed.webp" alt="Reward claimed screen" width="390" height="844" loading="lazy"></div><figcaption>Reward claimed</figcaption></figure>
      <figure><div class="phone"><img src="assets/shots/clubhouse.webp" alt="The Clubhouse team feed" width="390" height="844" loading="lazy"></div><figcaption>The Clubhouse</figcaption></figure>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="coaches-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">For coaches</p>
      <h2 id="coaches-h" class="display">See who put in the work.</h2>
    </div>
    <div class="grid-2" style="align-items:start">
      <div class="browser"><div class="browser-bar" aria-hidden="true"><i></i><i></i><i></i></div><img src="assets/shots/coach-web-review.webp" alt="The coach console's Review proof page on the web" width="1280" height="800" loading="lazy"></div>
      <ul class="ticks">
        <li>Assign one workout or a full weekly plan to the whole team, a position group or a few players</li>
        <li>Start from a drill library with written steps and demo videos</li>
        <li>Review photo and video proof and approve it in one tap</li>
        <li>Team challenges, leaderboards and a season pass with your own rewards</li>
        <li>Announcements, scheduled messages and reminders in the team inbox</li>
        <li>Moderate the team feed: reported posts and comments come straight to you</li>
        <li>Works on the web and in the same app your players use</li>
      </ul>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="safety-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">Safety</p>
      <h2 id="safety-h" class="display">A team space, not a social network.</h2>
    </div>
    <div class="grid-3">
      <div class="tile"><h3>13 and up</h3><p>We ask for a birth date at sign-up and don't allow accounts for anyone under 13.</p></div>
      <div class="tile"><h3>Private to the team</h3><p>Profiles of players under 18 are private to their team unless a guardian approves otherwise.</p></div>
      <div class="tile"><h3>Report and block</h3><p>Anyone can report a post or comment, or block another user. The team's coaches are alerted right away.</p></div>
    </div>
    <p class="muted" style="margin-top:24px">No ads, no selling data and no cross-app tracking. Read the <a href="{APP}/privacy">privacy policy</a>.</p>
  </div>
</section>

<section class="band" aria-labelledby="gp-cta-h">
  <div class="wrap">
    <div>
      <p class="label">Getting started</p>
      <h2 id="gp-cta-h" class="display">Coaches set up the team. Players join by invite.</h2>
    </div>
    <div class="actions">
      <a class="btn" href="contact.html">Set up your team</a>
      <a class="btn secondary" href="{APP}/login">Sign in</a>
    </div>
  </div>
</section>
'''
write("grind-pass.html", "The Grind Pass", "The Grind Pass by NXT Play Labs: coaches plan the work, players do it, and every rep earns XP, streaks and rewards.", gp)

# ---------------- About ----------------
about = f'''
<section class="page-hero">
  <div class="wrap">
    <p class="label">About</p>
    <h1 class="display">Next play.</h1>
    <p class="lede">Every player hears it after a strikeout or an error: flush it, next play. That's the idea behind the studio. Progress comes from what you do next, and the work nobody watches counts the most.</p>
  </div>
</section>

<section class="section" aria-labelledby="studio-h">
  <div class="wrap grid-2" style="align-items:start">
    <div class="prose">
      <p class="label">The studio</p>
      <h2 id="studio-h" class="display" style="font-size:var(--step-3)">A small studio for youth sports.</h2>
      <p>NXT Play Labs is a sports tech studio. We build software for young athletes and the coaches who train them, starting with baseball and softball.</p>
      <p>Our first product is The Grind Pass, a training app that turns the work between practices into something players want to do and coaches can actually see.</p>
      <p>We work closely with coaches and teams, ship in small steps, and keep what we build simple enough to use from the dugout.</p>
    </div>
    <aside class="board" aria-label="Studio facts">
      <div class="board-title"><span>Lineup card</span><span class="bulbs" aria-hidden="true"><i class="on"></i><i></i><i></i></span></div>
      <dl>
        <div class="board-row"><dt>Studio</dt><dd>NXT Play Labs</dd></div>
        <div class="board-row"><dt>Focus</dt><dd>Youth sports software</dd></div>
        <div class="board-row"><dt>First product</dt><dd>The Grind Pass</dd></div>
        <div class="board-row"><dt>Contact</dt><dd class="plain">{EMAIL}</dd></div>
      </dl>
    </aside>
  </div>
</section>

<section class="section" aria-labelledby="believe-h">
  <div class="wrap">
    <div class="section-head">
      <p class="label">What we believe</p>
      <h2 id="believe-h" class="display">Four rules we build by.</h2>
    </div>
    <div class="grid-2">
      <div class="tile"><h3>Reps over hype</h3><p>We reward the work: showing up, finishing the drill, keeping the streak. Not just the highlight.</p></div>
      <div class="tile"><h3>Coaches stay in charge</h3><p>Coaches decide what the team works on and what gets shared. The software follows their lead.</p></div>
      <div class="tile"><h3>Kids deserve better software</h3><p>No ads, no selling data, private profiles for minors and real tools for reporting and blocking.</p></div>
      <div class="tile"><h3>Fun is a feature</h3><p>XP, streaks and rewards exist because they make the next rep more likely. That's the whole point.</p></div>
    </div>
  </div>
</section>

<section class="band" aria-labelledby="about-cta-h">
  <div class="wrap">
    <div>
      <p class="label">Work with us</p>
      <h2 id="about-cta-h" class="display">Coaches, clubs and partners welcome.</h2>
    </div>
    <div class="actions"><a class="btn" href="contact.html">Get in touch</a></div>
  </div>
</section>
'''
write("about.html", "About NXT Play Labs", "NXT Play Labs is a sports tech studio building software for young athletes and their coaches.", about)

# ---------------- Support ----------------
def qa(q, a):
    return f'<details><summary>{q}</summary><div class="answer">{a}</div></details>'

groups = [
  ("Accounts", [
    ("How do I sign in?", f"<p>Use the email and password you signed up with, in the app or at <a href=\"{APP}/login\">app.nxtplaylabs.com</a>. It's the same account on every device.</p>"),
    ("I forgot my password.", f"<p>Tap “Forgot password” on the sign-in screen, or go to <a href=\"{APP}/forgot-password\">app.nxtplaylabs.com/forgot-password</a>. We'll email you a reset link.</p>"),
    ("Who can have an account?", "<p>The Grind Pass is for people 13 and older. We ask for a birth date when you sign up, or the first time you open the app if a coach invited you.</p>"),
    ("How do I delete my account?", f"<p>In the app: Profile → Settings → Delete account. Coaches: Settings → Delete account. You can also do it on the web at <a href=\"{APP}/delete-account\">app.nxtplaylabs.com/delete-account</a>, or email {EMAIL} from the address on your account.</p><p>Deleting removes your profile, training history, posts and uploads. Workouts and plans a coach made for the team stay with the team.</p>"),
  ]),
  ("Teams", [
    ("How do I join my team?", "<p>Your coach sends an invite link or gives you a team code. Open the link, or enter the code in the app, and you'll land on your team.</p>"),
    ("I'm on more than one team.", "<p>You can belong to several teams with one account and switch between them in the app.</p>"),
    ("How does a coach set up a team?", "<p>Email us to get your team set up. Once it's ready you can invite players and assistant coaches from the coach console or the app.</p>"),
  ]),
  ("Training", [
    ("Why do some workouts need a photo or video?", "<p>Coaches can ask for proof on any workout. Upload a photo or short video when you finish, and your coach reviews it.</p>"),
    ("How do XP and streaks work?", "<p>Finishing a workout earns XP. Training on back-to-back days builds your streak. XP moves you up levels in your team's season pass, which unlock badges and rewards.</p>"),
  ]),
  ("Safety", [
    ("How do I report a post or comment?", "<p>In the app, tap ••• on a post, or press and hold a comment, then choose Report. On the web, use the Report link. Your team's coaches are alerted right away.</p>"),
    ("How do I block someone?", "<p>Use the same menu and choose Block. You won't see their posts or comments anymore. You can unblock people from Profile → Settings.</p>"),
    ("Where are the privacy policy and terms?", f"<p>Read the <a href=\"{APP}/privacy\">privacy policy</a> and the <a href=\"{APP}/terms\">terms of use</a>.</p>"),
  ]),
]
faq_html = "".join(
  f'<div class="faq-group"><h2>{g}</h2><div class="faq">' + "".join(qa(q, a) for q, a in items) + "</div></div>"
  for g, items in groups
)
support = f'''
<section class="page-hero">
  <div class="wrap">
    <p class="label">Support</p>
    <h1 class="display">Help for players and coaches.</h1>
    <p class="lede">Answers to the questions we hear most about The Grind Pass. Still stuck? Email <strong>{EMAIL}</strong>.</p>
  </div>
</section>
<section class="section">
  <div class="wrap faq-groups">{faq_html}</div>
</section>
<section class="band" aria-labelledby="support-cta-h">
  <div class="wrap">
    <div>
      <p class="label">Didn't find it?</p>
      <h2 id="support-cta-h" class="display">Ask us directly.</h2>
    </div>
    <div class="actions"><a class="btn" href="contact.html">Contact support</a></div>
  </div>
</section>
'''
write("support.html", "Support · NXT Play Labs", "Help with The Grind Pass: accounts, teams, training, safety and deleting your account.", support)

# ---------------- Contact ----------------
def topic(t, d, subj):
    from urllib.parse import quote
    return f'<li><div><strong>{t}</strong><span>{d}</span></div><a class="subject" href="mailto:{EMAIL}?subject={quote(subj)}">Email · {html.escape(subj)}</a></li>'
contact = f'''
<section class="page-hero">
  <div class="wrap">
    <p class="label">Contact</p>
    <h1 class="display">Talk to the studio.</h1>
    <p class="lede">One inbox for everything. Put the topic in the subject line so it gets to the right person.</p>
  </div>
</section>
<section class="section">
  <div class="wrap grid-2" style="align-items:start">
    <div class="contact-card">
      <p class="label">Email</p>
      <div class="email-line">
        <span class="email" id="email-address">{EMAIL}</span>
        <button class="copy-btn" type="button" id="copy-email" data-copy="{EMAIL}">Copy</button>
      </div>
      <p class="muted">Safety problems on a team feed? Report them in the app first. That alerts the team's coaches right away.</p>
    </div>
    <ul class="topics">
      {topic("Set up a team", "Coaches and organizations who want The Grind Pass.", "Team setup")}
      {topic("Help with the app", "Sign-in trouble, bugs or questions about your account.", "Support")}
      {topic("Delete my account", "If you can't sign in to delete it yourself.", "Delete my account")}
      {topic("Partnerships", "Clubs, leagues, trainers and brands.", "Partnership")}
      {topic("Press", "Interviews and media questions.", "Press")}
    </ul>
  </div>
</section>
'''
write("contact.html", "Contact NXT Play Labs", "Contact NXT Play Labs about team setup, support, partnerships or press.", contact)
print("built")
