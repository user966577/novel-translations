"use strict";

// Novel Translations Plugin for LNReader
// Reads translated chapters from GitHub repository

const REPO_OWNER = 'user966577';
const REPO_NAME = 'novel-translations';
const BRANCH = 'main';
const BASE_RAW_URL = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}`;
const BASE_API_URL = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents`;

class NovelTranslationsPlugin {
  id = 'novel-translations';
  name = 'Novel Translations';
  version = '1.0.0';
  icon = 'src/en/noveltranslations/icon.png';
  site = `https://github.com/${REPO_OWNER}/${REPO_NAME}`;
  filters = {};

  async popularNovels(pageNo, { showLatestNovels, filters }) {
    if (pageNo > 1) return [];

    try {
      const response = await fetch(`${BASE_API_URL}/translated?ref=${BRANCH}`, {
        headers: { 'Accept': 'application/vnd.github.v3+json' }
      });
      const folders = await response.json();

      if (!Array.isArray(folders)) return [];

      const novels = [];

      for (const folder of folders) {
        if (folder.type !== 'dir') continue;

        try {
          const metaResponse = await fetch(
            `${BASE_RAW_URL}/translated/${encodeURIComponent(folder.name)}/metadata.json`
          );
          const metadata = await metaResponse.json();

          let coverUrl = '';
          if (metadata.cover_image) {
            coverUrl = `${BASE_RAW_URL}/translated/${encodeURIComponent(folder.name)}/${metadata.cover_image}`;
          }

          novels.push({
            name: metadata.title || folder.name,
            path: `${folder.name}`,
            cover: coverUrl,
          });
        } catch (e) {
          novels.push({
            name: folder.name,
            path: `${folder.name}`,
            cover: '',
          });
        }
      }

      return novels;
    } catch (error) {
      return [];
    }
  }

  async parseNovel(novelPath) {
    const folderName = novelPath;

    try {
      const metaResponse = await fetch(
        `${BASE_RAW_URL}/translated/${encodeURIComponent(folderName)}/metadata.json`
      );
      const metadata = await metaResponse.json();

      const filesResponse = await fetch(
        `${BASE_API_URL}/translated/${encodeURIComponent(folderName)}?ref=${BRANCH}`,
        { headers: { 'Accept': 'application/vnd.github.v3+json' } }
      );
      const files = await filesResponse.json();

      if (!Array.isArray(files)) {
        return { name: folderName, chapters: [] };
      }

      const chapterFiles = files
        .filter(f => f.name.match(/^chapter\d+\.txt$/))
        .sort((a, b) => {
          const numA = parseInt(a.name.match(/\d+/)[0]);
          const numB = parseInt(b.name.match(/\d+/)[0]);
          return numA - numB;
        });

      const chapters = chapterFiles.map(file => {
        const chapterNum = parseInt(file.name.match(/\d+/)[0]);
        const chapterTitle = metadata.chapter_titles?.[chapterNum] || `Chapter ${chapterNum}`;

        return {
          name: `Chapter ${chapterNum}: ${chapterTitle}`,
          path: `${folderName}/${file.name}`,
          chapterNumber: chapterNum,
        };
      });

      let coverUrl = '';
      if (metadata.cover_image) {
        coverUrl = `${BASE_RAW_URL}/translated/${encodeURIComponent(folderName)}/${metadata.cover_image}`;
      }

      return {
        name: metadata.title || folderName,
        cover: coverUrl,
        summary: metadata.synopsis || '',
        author: metadata.author || 'Unknown',
        status: 'Ongoing',
        genres: 'Web Novel, Cultivation',
        chapters,
      };
    } catch (error) {
      return { name: folderName, chapters: [] };
    }
  }

  async parseChapter(chapterPath) {
    try {
      const response = await fetch(`${BASE_RAW_URL}/translated/${encodeURIComponent(chapterPath).replace(/%2F/g, '/')}`);
      const text = await response.text();

      const paragraphs = text
        .split(/\n\n+/)
        .filter(p => p.trim())
        .map(p => `<p>${p.trim().replace(/\n/g, '<br>').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/&lt;br&gt;/g, '<br>')}</p>`)
        .join('\n');

      return paragraphs;
    } catch (error) {
      return '<p>Error loading chapter content.</p>';
    }
  }

  async searchNovels(searchTerm, pageNo) {
    if (pageNo > 1) return [];

    const allNovels = await this.popularNovels(1, {});
    const searchLower = searchTerm.toLowerCase();

    return allNovels.filter(novel =>
      novel.name.toLowerCase().includes(searchLower)
    );
  }
}

module.exports = new NovelTranslationsPlugin();
