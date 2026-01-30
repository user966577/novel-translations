"use strict";

// Novel Translations Plugin for LNReader
// Reads translated chapters from GitHub repository

var REPO_OWNER = 'user966577';
var REPO_NAME = 'novel-translations';
var BRANCH = 'main';
// Hybrid approach:
// - jsDelivr CDN for chapter content (large files, good caching)
// - GitHub API for metadata.json (small file, needs fresh data, avoids CDN cache issues)
var BASE_CDN_URL = 'https://cdn.jsdelivr.net/gh/' + REPO_OWNER + '/' + REPO_NAME + '@' + BRANCH;
var BASE_API_URL = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/contents';

// Helper to fetch metadata.json via GitHub API (always fresh, no CDN caching)
async function fetchMetadata(folderName) {
  var apiUrl = BASE_API_URL + '/translated/' + encodeURIComponent(folderName) + '/metadata.json?ref=' + BRANCH;
  console.log('[NovelTranslations] Fetching metadata from:', apiUrl);

  var response = await fetch(apiUrl, {
    headers: { 'Accept': 'application/vnd.github.v3+json' }
  });

  if (!response.ok) {
    console.log('[NovelTranslations] Metadata fetch failed:', response.status);
    return null;
  }

  var data = await response.json();
  // GitHub API returns content as base64
  var content = atob(data.content);
  var metadata = JSON.parse(content);
  console.log('[NovelTranslations] Loaded metadata, chapters:', Object.keys(metadata.chapter_titles || {}).length);
  return metadata;
}

function NovelTranslationsPlugin() {
  this.id = 'novel-translations';
  this.name = 'Novel Translations';
  this.version = '1.1.1';
  this.icon = 'src/en/noveltranslations/icon.png';
  this.site = 'https://github.com/' + REPO_OWNER + '/' + REPO_NAME;
  this.filters = {};
}

NovelTranslationsPlugin.prototype.popularNovels = async function(pageNo, options) {
  if (pageNo > 1) return [];

  try {
    var response = await fetch(BASE_API_URL + '/translated?ref=' + BRANCH, {
      headers: { 'Accept': 'application/vnd.github.v3+json' }
    });
    var folders = await response.json();

    if (!Array.isArray(folders)) return [];

    var novels = [];

    for (var i = 0; i < folders.length; i++) {
      var folder = folders[i];
      if (folder.type !== 'dir') continue;

      var novelPath = folder.name;

      try {
        var metadata = await fetchMetadata(folder.name);

        var coverUrl = '';
        if (metadata && metadata.cover_image) {
          coverUrl = BASE_CDN_URL + '/translated/' + encodeURIComponent(folder.name) + '/' + metadata.cover_image;
          console.log('[NovelTranslations] Cover URL:', coverUrl);
        }

        novels.push({
          name: (metadata && metadata.title) || folder.name,
          path: novelPath,
          url: novelPath,
          cover: coverUrl
        });
      } catch (e) {
        novels.push({
          name: folder.name,
          path: novelPath,
          url: novelPath,
          cover: ''
        });
      }
    }

    return novels;
  } catch (error) {
    return [];
  }
};

NovelTranslationsPlugin.prototype.parseNovel = async function(novelUrl) {
  var folderName = novelUrl;

  try {
    var metadata = await fetchMetadata(folderName);

    if (!metadata) {
      return { path: folderName, url: folderName, name: folderName, chapters: [] };
    }

    var filesResponse = await fetch(
      BASE_API_URL + '/translated/' + encodeURIComponent(folderName) + '?ref=' + BRANCH,
      { headers: { 'Accept': 'application/vnd.github.v3+json' } }
    );
    var files = await filesResponse.json();

    if (!Array.isArray(files)) {
      return { path: folderName, url: folderName, name: folderName, chapters: [] };
    }

    var chapterFiles = files
      .filter(function(f) { return /^chapter\d+\.txt$/.test(f.name); })
      .sort(function(a, b) {
        var numA = parseInt(a.name.match(/\d+/)[0]);
        var numB = parseInt(b.name.match(/\d+/)[0]);
        return numA - numB;
      });

    var chapters = chapterFiles.map(function(file) {
      var chapterNum = parseInt(file.name.match(/\d+/)[0]);
      var chapterTitle = (metadata.chapter_titles && metadata.chapter_titles[chapterNum]) || ('Chapter ' + chapterNum);
      var chapterPath = folderName + '/' + file.name;

      return {
        name: 'Chapter ' + chapterNum + ': ' + chapterTitle,
        path: chapterPath,
        url: chapterPath,
        chapterNumber: chapterNum
      };
    });

    var coverUrl = '';
    if (metadata.cover_image) {
      coverUrl = BASE_CDN_URL + '/translated/' + encodeURIComponent(folderName) + '/' + metadata.cover_image;
    }

    return {
      path: folderName,
      url: folderName,
      name: metadata.title || folderName,
      cover: coverUrl,
      summary: metadata.synopsis || '',
      author: metadata.author || 'Unknown',
      status: 'Ongoing',
      genres: 'Web Novel, Cultivation',
      chapters: chapters
    };
  } catch (error) {
    return { path: folderName, url: folderName, name: folderName, chapters: [] };
  }
};

NovelTranslationsPlugin.prototype.parseChapter = async function(chapterUrl) {
  try {
    // Use jsDelivr CDN for chapter content (good caching for large files)
    var url = BASE_CDN_URL + '/translated/' + chapterUrl.split('/').map(encodeURIComponent).join('/');
    var response = await fetch(url);
    var text = await response.text();

    var paragraphs = text
      .split(/\n\n+/)
      .filter(function(p) { return p.trim(); })
      .map(function(p) {
        var escaped = p.trim()
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\n/g, '<br>');
        return '<p>' + escaped + '</p>';
      })
      .join('\n');

    return paragraphs;
  } catch (error) {
    return '<p>Error loading chapter content.</p>';
  }
};

NovelTranslationsPlugin.prototype.searchNovels = async function(searchTerm, pageNo) {
  if (pageNo > 1) return [];

  var allNovels = await this.popularNovels(1, {});
  var searchLower = searchTerm.toLowerCase();

  return allNovels.filter(function(novel) {
    return novel.name.toLowerCase().indexOf(searchLower) !== -1;
  });
};

exports.default = new NovelTranslationsPlugin();
