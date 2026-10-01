// Karma configuration file, see link for more information
// https://karma-runner.github.io/1.0/config/configuration-file.html

const fs = require('fs');

// No Chrome installed (e.g. the dev container): fall back to the Chromium
// that Playwright (e2e tests) already downloaded. CHROME_BIN set by hand, or
// a system Chrome as on the GitHub Actions runners, takes precedence.
if (!process.env.CHROME_BIN) {
  try {
    const playwrightChromium = require('@playwright/test').chromium.executablePath();
    if (fs.existsSync(playwrightChromium)) {
      process.env.CHROME_BIN = playwrightChromium;
    }
  } catch {
    // @playwright/test not installed: let karma-chrome-launcher look for Chrome.
  }
}

// Chrome refuses to start as root without --no-sandbox (dev containers
// often run as root); the sandbox stays on for any other user.
const runsAsRoot = process.getuid?.() === 0;

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('@angular-devkit/build-angular/plugins/karma')
    ],
    client: {
      jasmine: {
        // you can add configuration options for Jasmine here
        // the possible options are listed at https://jasmine.github.io/api/edge/Configuration.html
        // for example, you can disable the random execution with `random: false`
        // or set a specific seed with `seed: 4321`
      },
    },
    jasmineHtmlReporter: {
      suppressAll: true // removes the duplicated traces
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/alfred_react'),
      subdir: '.',
      reporters: [
        { type: 'html' },
        { type: 'text-summary' }
      ]
    },
    reporters: ['progress', 'kjhtml'],
    customLaunchers: {
      ChromeHeadlessCI: {
        base: 'ChromeHeadless',
        flags: runsAsRoot ? ['--no-sandbox'] : []
      }
    },
    browsers: ['ChromeHeadlessCI'],
    restartOnFileChange: true
  });
};
