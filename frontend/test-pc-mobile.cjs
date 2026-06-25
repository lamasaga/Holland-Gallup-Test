const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const FRONTEND = 'http://localhost:5175';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUTPUT = path.join(__dirname, 'screenshots-responsive', 'tests');

const VIEWPORTS = {
  pc: { width: 1280, height: 800, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
  mobile: { width: 375, height: 667, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
};

const TEST_ACCOUNTS = [
  { username: 'sim_student_ria', password: 'pass123', label: 'RIA学生' },
  { username: 'sim_student_sec', password: 'pass123', label: 'SEC学生' },
  { username: 'sim_student_random', password: 'pass123', label: '随机学生' },
  { username: 'sim_student_c_only', password: 'pass123', label: 'C独高学生' },
  { username: 'sim_student_all5', password: 'pass123', label: '全5学生' },
  { username: 'edge_incomplete', password: 'pass123', label: '未完成测评', skipCompletion: true },
  { username: 'edge_retake', password: 'pass123', label: '重测学生' },
];

async function loginApi(username, password, role = 'student') {
  const res = await fetch(`${FRONTEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, role }),
  });
  if (!res.ok) throw new Error(`Login failed for ${username}: ${res.status}`);
  return res.json();
}

async function setAuth(page, user) {
  await page.evaluate((token, u) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify({
      id: u.user_id,
      role: u.role,
      display_name: u.display_name,
      username: u.username,
    }));
  }, user.access_token, user);
}

async function screenshot(page, filename) {
  const file = path.join(OUTPUT, filename);
  await page.screenshot({ path: file, fullPage: true });
  console.log('Saved:', file);
}

async function ensureCompleted(page, student) {
  const progress = await page.evaluate(async () => {
    const res = await fetch('/api/assessments/progress', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    });
    return res.json();
  });
  console.log(`  ${student.label} progress:`, progress.holland_done, progress.gallup_done);

  if (!progress.holland_done) {
    console.log('  Answering Holland...');
    await page.goto(`${FRONTEND}/student/holland`, { waitUntil: 'networkidle2' });
    await page.waitForSelector('.question-card', { timeout: 10000 });
    for (let i = 0; i < 60; i++) {
      const buttons = await page.$$('.options button');
      if (!buttons.length) break;
      await buttons[2].click();
      await new Promise(r => setTimeout(r, 120));
    }
    await new Promise(r => setTimeout(r, 500));
  }

  if (!progress.gallup_done) {
    console.log('  Answering Gallup...');
    await page.goto(`${FRONTEND}/student/gallup`, { waitUntil: 'networkidle2' });
    await page.waitForSelector('.question-card', { timeout: 10000 });
    for (let i = 0; i < 180; i++) {
      const buttons = await page.$$('.options button');
      if (!buttons.length) break;
      await buttons[2].click();
      await new Promise(r => setTimeout(r, 100));
    }
    await new Promise(r => setTimeout(r, 500));
  }
}

async function captureForRole(page, user, teacher, label, slug) {
  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    await page.setViewport(vp);

    // student dashboard
    await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
    await setAuth(page, user);
    await page.goto(`${FRONTEND}/student`, { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 1000));
    await screenshot(page, `${slug}_dashboard_${vpName}.png`);

    // student report
    await page.goto(`${FRONTEND}/student/report`, { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 1200));
    await screenshot(page, `${slug}_report_${vpName}.png`);

    // teacher report (only for completed students)
    if (teacher && !user.username.includes('incomplete')) {
      await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
      await setAuth(page, teacher);
      await page.goto(`${FRONTEND}/teacher/report/${user.user_id}`, { waitUntil: 'domcontentloaded' });
      await new Promise(r => setTimeout(r, 1200));
      await screenshot(page, `${slug}_teacher-report_${vpName}.png`);
    }
  }
}

function safeSlug(label) {
  return label.replace(/[^\w\u4e00-\u9fa5]/g, '_');
}

(async () => {
  fs.mkdirSync(OUTPUT, { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const teacher = await loginApi('teacher', 'teacher123', 'teacher');
    console.log('Teacher logged in:', teacher.display_name);

    const workPage = await browser.newPage();
    workPage.on('dialog', async dialog => await dialog.dismiss());

    for (const account of TEST_ACCOUNTS) {
      const student = await loginApi(account.username, account.password, 'student');
      console.log(`\nTesting ${account.label} (${account.username})`);

      if (!account.skipCompletion) {
        await workPage.setViewport(VIEWPORTS.pc);
        await workPage.goto(`${FRONTEND}/login`, { waitUntil: 'networkidle2' });
        await setAuth(workPage, student);
        await ensureCompleted(workPage, account);
      }

      await captureForRole(workPage, student, teacher, account.label, safeSlug(account.label));
    }

    await workPage.close();
    console.log('\nAll test screenshots saved to:', OUTPUT);
  } catch (err) {
    console.error(err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
