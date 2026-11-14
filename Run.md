# Run guide for AgriSheba

This project is a static HTML-based agricultural dashboard and data research prototype. It can be opened locally without a build step.

## Option 1: run a local web server

From the project root:

```bash
cd "E:\Users\ismail\Desktop\agree_sheba"
python -m http.server 8000
```

Then open one of these in your browser:

- http://localhost:8000/
- http://localhost:8000/index.html

## Option 2: open directly

You can also open `index.html` directly in a browser by double-clicking it or using the browser's "Open File" option.

Note: using a local web server is usually more reliable for static pages that rely on browser loading behavior.

## Useful notes

- The project root contains multiple demo HTML files such as `index.html`, `index copy.html`, and `index copy 2.html`.
- `index.html` is the main entry point for the dashboard-style interface.
- Data files live under `data/`, and Python scripts under `data/datacollect/` and `data/nasa/` are used to process source datasets.

## Troubleshooting

- If the page does not load correctly, try the local server method above.
- If a browser blocks local file references, use the HTTP server.
- If scripts or files are missing, verify the repo is complete and the data folders are present.
