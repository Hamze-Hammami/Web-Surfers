const puppeteer = require('puppeteer');
const readline = require('readline');

const url = 'https://www.speedtypingonline.com/games/type-the-alphabet.php';
const delayBetweenLetters = 0;

const parseLetters = async (page) => {
  const targetElement = await page.$('#blockLine0');
  const letterElements = await targetElement.$$('span.nxtLetter, span.plainText');
  const letters = [];
  for (const element of letterElements) {
    const text = await element.evaluate((el) => el.textContent);
    if (text === '\u00A0') {
      letters.push(' ');
    } else {
      letters.push(text);
    }
  }
  return letters.join('');
};

const typeLetters = async (page, letters) => {
  await page.keyboard.type(letters, { delay: delayBetweenLetters });
  const lastCharacter = letters.slice(-1);
  await page.keyboard.type(lastCharacter);
};

const checkFastestTime = async (page) => {
  const fastestTimeElement = await page.$('#wbkScore');
  const fastestTime = await fastestTimeElement.evaluate((el) => el.textContent);
  const modeElement = await page.$('.ui-selectmenu-text');
  const modeText = await modeElement.evaluate((el) => el.textContent);

  let maxFastestTime = modeText.includes('(with Spaces)') ? 0.15 : 0.06;

  return parseFloat(fastestTime) <= maxFastestTime;
};

const runFastLoop = async (page) => {
  let tryCount = 1;
  let fastestTimeReached = false;

  while (true) {
    console.log(`Try #${tryCount}`);
    await page.click('#resetBtn');
    const letters = await parseLetters(page);
    await typeLetters(page, letters);

    tryCount++;

    if (tryCount > 25) {
      console.log('Maximum number of tries reached.');
      break;
    }

    fastestTimeReached = await checkFastestTime(page);
    if (fastestTimeReached) {
      console.log('Fastest time already reached.');
      break;
    }
  }

  if (!fastestTimeReached) {
    console.log('Fastest time not yet reached.');
  }
};

(async () => {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(url, { waitUntil: 'networkidle0' });

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  rl.on('line', async (input) => {
    if (input === 'q') {
      rl.close();
      await browser.close();
    } else if (!isNaN(input)) {
      const repeatCount = parseInt(input, 10);
      for (let i = 0; i < repeatCount; i++) {
        console.log(`Reset ${i + 1}`);
        await page.click('#resetBtn');
        const letters = await parseLetters(page);
        await typeLetters(page, letters);
      }
    } else if (input === 'fast') {
      const fastestTimeReached = await checkFastestTime(page);
      if (fastestTimeReached) {
        console.log('Fastest time already reached.');
      } else {
        await runFastLoop(page);
      }
    } else {
      console.log('Invalid input. Please enter a number, "fast", or "q" to quit.');
    }
  });

  console.log('Enter a number to specify the number of repetitions, "fast" for continuous tries, or "q" to quit:');
})();
