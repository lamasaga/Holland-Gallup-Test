const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const FRONTEND = 'http://localhost:5175';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUTPUT = path.join(__dirname, 'screenshots-responsive');

const VIEWPORTS = {
  'iphone-se': { width: 375, height: 667, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  'iphone-14': { width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
  'ipad-portrait': { width: 810, height: 1080, deviceScaleFactor: 2, isMobile: false, hasTouch: true },
  'ipad-landscape': { width: 1080, height: 810, deviceScaleFactor: 2, isMobile: false, hasTouch: true },
  'desktop': { width: 1280, height: 800, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
};

const PAGES = [
  { name: 'login', path: '/login', role: null },
  { name: 'student-dashboard', path: '/student', role: 'student' },
  { name: 'holland-assessment', path: '/student/holland', role: 'student' },
  { name: 'student-report', path: '/student/report', role: 'student' },
  { name: 'teacher-dashboard', path: '/teacher', role: 'teacher' },
  { name: 'teacher-report', path: '/teacher/report/1c2d3e4f-1111-2222-3333-444455556666', role: 'teacher' },
];

// 使用已存在的模拟学生用户ID（sim_openness_01 的固定 uuid）
const STUDENT_ID = '1c2d3e4f-1111-2222-3333-444455556666';

async function loginApi(username, password, role) {
  const res = await fetch(`${FRONTEND}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, role }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
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

async function screenshot(page, label, vpName) {
  const file = path.join(OUTPUT, `${label}_${vpName}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log('Saved:', file);
}

(async () => {
  fs.mkdirSync(OUTPUT, { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    // 预登录两个角色
    const student = await loginApi('sim_openness_01', 'Sim@1234!', 'student');
    const teacher = await loginApi('teacher', 'teacher123', 'teacher');
    console.log('Logged in student:', student.display_name);
    console.log('Logged in teacher:', teacher.display_name);

    // 先给学生提交一次完整测评，确保报告页有内容
    const stuPage = await browser.newPage();
    await stuPage.setViewport(VIEWPORTS.desktop);
    await stuPage.goto(`${FRONTEND}/login`, { waitUntil: 'networkidle2' });
    await setAuth(stuPage, student);

    // 如果还没完成测评，自动填完
    const progressRes = await stuPage.evaluate(async () => {
      const res = await fetch('/api/assessments/progress', { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
      return res.json();
    });
    console.log('Student progress:', progressRes.holland_done, progressRes.gallup_done);

    if (!progressRes.holland_done) {
      console.log('Answering Holland...');
      await stuPage.goto(`${FRONTEND}/student/holland`, { waitUntil: 'networkidle2' });
      await stuPage.waitForSelector('.question-card', { timeout: 10000 });
      for (let i = 0; i < 60; i++) {
        const buttons = await stuPage.$$('.options button');
        if (!buttons.length) break;
        await buttons[2].click();
        await new Promise(r => setTimeout(r, 150));
      }
      await new Promise(r => setTimeout(r, 1000));
    }
    if (!progressRes.gallup_done) {
      console.log('Answering Gallup...');
      await stuPage.goto(`${FRONTEND}/student/gallup`, { waitUntil: 'networkidle2' });
      await stuPage.waitForSelector('.question-card', { timeout: 10000 });
      for (let i = 0; i < 180; i++) {
        const buttons = await stuPage.$$('.options button');
        if (!buttons.length) break;
        await buttons[2].click();
        await new Promise(r => setTimeout(r, 120));
      }
      await new Promise(r => setTimeout(r, 1000));
    }
    await stuPage.close();

    // 截图循环
    for (const pageConfig of PAGES) {
      const user = pageConfig.role === 'teacher' ? teacher : student;
      const targetPath = pageConfig.name === 'teacher-report'
        ? `/teacher/report/${student.user_id}`
        : pageConfig.path;

      for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
        const page = await browser.newPage();
        await page.setViewport(vp);
        await page.goto(`${FRONTEND}/login`, { waitUntil: 'networkidle2' });
        await setAuth(page, user);
        await page.goto(`${FRONTEND}${targetPath}`, { waitUntil: 'networkidle2' });
        await new Promise(r => setTimeout(r, 800));
        await screenshot(page, pageConfig.name, vpName);
        await page.close();
      }
    }

    console.log('\nAll screenshots saved to:', OUTPUT);
  } catch (err) {
    console.error(err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
