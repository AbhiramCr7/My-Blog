# 0xAbhiram Blog

Red teaming, Active Directory, product security and GRC automation notes by **Abhiram SS (0xAbhiram)**.

Live: https://0xabhiram-blogs.vercel.app

## Layout

| Path | What it is |
| --- | --- |
| `posts/` | Blog posts in Markdown with YAML front matter |
| `build.py` | Generates every HTML page into `public/` |
| `public/` | The website: generated pages plus `styles.css`, `main.js`, `assets/` |
| `vercel.json` | Serves `public/` as a static site (no build step on Vercel) |

## Writing a post

1. Add `posts/my-post.md` with `title`, `date`, `tags` and `description` in the front matter.
2. Register it in the `POSTS` list in `build.py` (output page, cover image in `public/assets/`, card title).
3. Build and preview:

   ```sh
   npm install      # first time only
   npm run build
   npm run serve    # http://localhost:5500
   ```

4. Commit everything, including `public/`, and push. Vercel deploys `main` automatically.
