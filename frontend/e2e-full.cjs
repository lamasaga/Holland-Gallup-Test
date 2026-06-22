const puppeteer = require('puppeteer-core');

const FRONTEND = 'http://localhost:5173';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();
    page.on('console', msg => console.log('CONSOLE:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    page.on('dialog', async dialog => {
      console.log('DIALOG:', dialog.type(), dialog.message());
      await dialog.dismiss();
    });

    console.log('Logging in as student via API...');
    await page.goto(`${FRONTEND}/login`, { waitUntil: 'networkidle2' });
    const loginRes = await page.evaluate(async () => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'student', password: 'student123', role: 'student' })
      });
      return res.json();
    });
    await page.evaluate((token) => {
      localStorage.setItem('token', token.access_token);
      localStorage.setItem('user', JSON.stringify({ id: token.user_id, role: token.role, display_name: token.display_name }));
    }, loginRes);
    console.log('Logged in:', loginRes.display_name);

    async function answerHolland() {
      console.log('\n=== Holland Assessment ===');
      await page.goto(`${FRONTEND}/student/holland`, { waitUntil: 'networkidle2' });
      await page.waitForSelector('.question-card', { timeout: 10000 });

      let qNum = 1;
      while (true) {
        const card = await page.$('.question-card');
        if (!card) break;
        const text = await card.$eval('h3', el => el.textContent).catch(() => 'no h3');
        if (qNum % 10 === 1 || qNum === 60) console.log('Answering:', text);

        const buttons = await page.$$('.options button');
        if (buttons.length === 0) break;
        await buttons[2].click(); // score 3
        await new Promise(r => setTimeout(r, 350));

        const navButtons = await page.$$('div.nav-buttons button');
        const lastBtn = navButtons[navButtons.length - 1];
        const lastText = await page.evaluate(el => el.textContent, lastBtn);
        const disabled = await page.evaluate(el => el.disabled, lastBtn);
        if (lastText.includes('提交') && !disabled) {
          console.log('Submitting Holland...');
          await lastBtn.click();
          await new Promise(r => setTimeout(r, 3000));
          break;
        }
        qNum++;
      }
      console.log('Holland final URL:', page.url());
    }

    async function answerGallup() {
      console.log('\n=== Gallup Assessment ===');
      await page.goto(`${FRONTEND}/student/gallup`, { waitUntil: 'networkidle2' });
      await page.waitForSelector('.question-card', { timeout: 10000 });

      let qNum = 1;
      while (true) {
        const card = await page.$('.question-card');
        if (!card) break;
        const text = await card.$eval('h3', el => el.textContent).catch(() => 'no h3');
        if (qNum % 30 === 1 || qNum >= 178) console.log('Answering:', text);

        const buttons = await page.$$('.options button');
        if (buttons.length === 0) break;
        await buttons[3].click(); // 比较认同B
        await new Promise(r => setTimeout(r, 350));

        const navButtons = await page.$$('div.nav-buttons button');
        const lastBtn = navButtons[navButtons.length - 1];
        const lastText = await page.evaluate(el => el.textContent, lastBtn);
        const disabled = await page.evaluate(el => el.disabled, lastBtn);
        if (lastText.includes('提交') && !disabled) {
          console.log('Submitting Gallup...');
          await lastBtn.click();
          await new Promise(r => setTimeout(r, 3000));
          break;
        }
        qNum++;
      }
      console.log('Gallup final URL:', page.url());
    }

    async function checkReport() {
      console.log('\n=== Student Report ===');
      await page.goto(`${FRONTEND}/student/report`, { waitUntil: 'networkidle2' });
      await page.waitForFunction(() => document.querySelector('.kz-report') || document.querySelector('h1'), { timeout: 10000 });
      const title = await page.$eval('h1', el => el.textContent).catch(() => 'unknown');
      console.log('Report title:', title);
      const reportText = await page.$eval('.kz-report', el => el.textContent).catch(() => '');
      const hollandMatch = reportText.match(/Holland\s*三码\s*\/\s*Holland Code[：:]\s*(\w{3})/);
      const gallupMatch = reportText.match(/优势领域\s*\/\s*Leading Strength Domain[：:]\s*([^\n]+)/);
      const holland = hollandMatch ? hollandMatch[1] : 'N/A';
      const gallup = gallupMatch ? gallupMatch[1].trim() : 'N/A';
      console.log('Holland:', holland);
      console.log('Gallup domain:', gallup);
      if (!reportText.includes('我的核心结果') && !reportText.includes('My Core Results')) {
        throw new Error('Report content not rendered');
      }
      if (holland === 'N/A' || gallup === 'N/A') {
        throw new Error('Holland or Gallup info not rendered');
      }
    }

    await answerHolland();
    await answerGallup();
    await checkReport();

    console.log('\n✅ Full E2E test passed.');
  } catch (err) {
    console.error('TEST ERROR:', err.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
