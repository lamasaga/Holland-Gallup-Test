const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
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

    console.log('Opening login page...');
    await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle2' });

    console.log('Logging in as student...');
    await page.waitForSelector('input[type="text"]');
    await page.type('input[type="text"]', 'student');
    await page.type('input[type="password"]', 'student123');
    await page.click('button[type="submit"]');

    console.log('Waiting for dashboard...');
    await page.waitForSelector('h1', { timeout: 5000 });
    const title = await page.$eval('h1', el => el.textContent);
    console.log('Dashboard title:', title);

    // Reset gallup assessment by calling backend directly
    console.log('Resetting gallup assessment via API...');
    const loginRes = await page.evaluate(async () => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'student', password: 'student123', role: 'student' })
      });
      return res.json();
    });
    console.log('Login token obtained');

    await page.evaluate(async (token) => {
      localStorage.setItem('token', token.access_token);
      localStorage.setItem('user', JSON.stringify({ id: token.user_id, role: token.role, display_name: token.display_name }));
    }, loginRes);

    console.log('Navigating to Gallup assessment...');
    await page.goto('http://localhost:5173/student/gallup', { waitUntil: 'networkidle2' });

    console.log('Waiting for question card...');
    await page.waitForSelector('.question-card', { timeout: 10000 });

    let qNum = 1;
    while (qNum <= 185) {
      const card = await page.$('.question-card');
      if (!card) {
        console.log('No question card found at step', qNum);
        break;
      }
      const questionText = await card.$eval('h3', el => el.textContent).catch(() => 'no h3');
      console.log('Answering:', questionText);

      const buttons = await page.$$('.options button');
      if (buttons.length === 0) {
        console.log('No option buttons found');
        break;
      }
      const btnTexts = await Promise.all(buttons.map(b => page.evaluate(el => el.textContent, b)));
      if (qNum === 180) {
        console.log('Option buttons:', btnTexts, 'count:', buttons.length);
      }
      // Click option index 3 (比较认同B, value=-1)
      await buttons[3].click();
      await new Promise(r => setTimeout(r, 800));
      
      // Check selected state
      const selectedCount = await page.evaluate(() => document.querySelectorAll('.options button.selected').length);
      if (qNum === 180) {
        console.log('Selected count after click:', selectedCount);
      }

      // Check if submit button is now enabled
      const navButtons = await page.$$('div.nav-buttons button');
      if (navButtons.length > 0) {
        const lastBtn = navButtons[navButtons.length - 1];
        const lastBtnText = await page.evaluate(el => el.textContent, lastBtn);
        const lastBtnDisabled = await page.evaluate(el => el.disabled, lastBtn);
        if (qNum === 180) {
          console.log('Nav button:', lastBtnText, 'disabled:', lastBtnDisabled);
        }
        if (lastBtnText.includes('提交') && !lastBtnDisabled) {
          console.log('Clicking submit...');
          await lastBtn.click();
          await new Promise(r => setTimeout(r, 3000));
          break;
        }
      }

      qNum++;
    }

    console.log('Finished answering questions');
    const finalTitle = await page.$eval('h1', el => el.textContent).catch(() => 'unknown');
    console.log('Final page title:', finalTitle);
    const finalUrl = page.url();
    console.log('Final URL:', finalUrl);

  } catch (err) {
    console.error('TEST ERROR:', err.message);
  } finally {
    await browser.close();
  }
})();
