from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://httpbin.org/ip")
        print(page.inner_text("pre"))
        browser.close()

if __name__ == "__main__":
    main()
