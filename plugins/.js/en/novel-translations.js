"use strict";

// Novel Translations Plugin for LNReader
// Reads translated chapters from GitHub repository

var REPO_OWNER = 'user966577';
var REPO_NAME = 'novel-translations';
var BRANCH = 'main';
var BASE_URL = 'https://raw.githubusercontent.com/' + REPO_OWNER + '/' + REPO_NAME + '/' + BRANCH;

function NovelTranslationsPlugin() {
  this.id = 'novel-translations';
  this.name = 'Novel Translations';
  this.version = '1.2.2';
  this.icon = 'src/en/noveltranslations/icon.png';
  this.site = 'https://github.com/' + REPO_OWNER + '/' + REPO_NAME;
  this.filters = {};
}

NovelTranslationsPlugin.prototype.popularNovels = async function(pageNo, options) {
  if (pageNo > 1) return [];

  try {
    // Get list of novel folders
    var response = await fetch(
      'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/contents/translated?ref=' + BRANCH
    );
    var folders = await response.json();

    if (!Array.isArray(folders)) return [];

    var novels = [];

    for (var i = 0; i < folders.length; i++) {
      var folder = folders[i];
      if (folder.type !== 'dir') continue;

      var novelPath = folder.name;

      try {
        // Fetch metadata with cache-busting timestamp
        var metaUrl = BASE_URL + '/translated/' + encodeURIComponent(folder.name) + '/metadata.json?t=' + Date.now();
        var metaResponse = await fetch(metaUrl);
        var metadata = await metaResponse.json();

        var coverUrl = '';
        if (metadata.cover_image) {
          coverUrl = BASE_URL + '/translated/' + encodeURIComponent(folder.name) + '/' + metadata.cover_image;
        }

        novels.push({
          name: metadata.title || folder.name,
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
    // Fetch metadata with cache-busting timestamp
    var metaUrl = BASE_URL + '/translated/' + encodeURIComponent(folderName) + '/metadata.json?t=' + Date.now();
    var metaResponse = await fetch(metaUrl);

    if (!metaResponse.ok) {
      return { path: folderName, url: folderName, name: folderName, chapters: [] };
    }

    var metadata = await metaResponse.json();

    // Get chapter files list
    var filesResponse = await fetch(
      'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/contents/translated/' + encodeURIComponent(folderName) + '?ref=' + BRANCH
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
      coverUrl = BASE_URL + '/translated/' + encodeURIComponent(folderName) + '/' + metadata.cover_image;
    }

    var synopsis = metadata.synopsis || '';

    return {
      path: folderName,
      url: folderName,
      name: metadata.title || folderName,
      cover: coverUrl,
      summary: synopsis,
      description: synopsis,
      author: metadata.author || 'Unknown',
      artist: '',
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
    var url = BASE_URL + '/translated/' + chapterUrl.split('/').map(encodeURIComponent).join('/');
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
