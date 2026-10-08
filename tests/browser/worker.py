"""Await actual worker ownership without eval-based polling under strict CSP."""

from playwright.sync_api import Page


def wait_for_worker_control(page: Page) -> None:
    page.evaluate("""() => new Promise((resolve, reject) => {
        const worker = navigator.serviceWorker;
        if (worker.controller) { resolve(); return; }
        const timeout = setTimeout(() => {
            worker.removeEventListener('controllerchange', controlled);
            reject(new Error('Service worker did not control the page within 5s'));
        }, 5000);
        function controlled() {
            if (!worker.controller) return;
            clearTimeout(timeout);
            worker.removeEventListener('controllerchange', controlled);
            resolve();
        }
        worker.addEventListener('controllerchange', controlled);
    })""")
