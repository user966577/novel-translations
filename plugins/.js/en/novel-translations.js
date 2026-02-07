"use strict";

// Novel Translations Plugin for LNReader
// Reads translated chapters from GitHub Pages

var BASE_URL = 'https://user966577.github.io/novel-translations';

function NovelTranslationsPlugin() {
  this.id = 'novel-translations';
  this.name = 'Novel Translations';
  this.version = '1.4.0';
  this.icon = 'src/en/noveltranslations/icon.png';
  this.site = 'https://github.com/user966577/novel-translations';
  this.filters = {};
}

NovelTranslationsPlugin.prototype.popularNovels = async function(pageNo, options) {
  if (pageNo > 1) return [];

  try {
    var response = await fetch(BASE_URL + '/translated/index.json');
    var folders = await response.json();

    if (!Array.isArray(folders)) return [];

    var novels = [];

    for (var i = 0; i < folders.length; i++) {
      var folder = folders[i];
      if (folder.type !== 'dir') continue;

      var novelPath = folder.name;

      try {
        var metaResponse = await fetch(
          BASE_URL + '/translated/' + encodeURIComponent(folder.name) + '/metadata.json'
        );
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
    var metaResponse = await fetch(
      BASE_URL + '/translated/' + encodeURIComponent(folderName) + '/metadata.json'
    );

    if (!metaResponse.ok) {
      return { path: folderName, url: folderName, name: folderName, chapters: [] };
    }

    var metadata = await metaResponse.json();

    var indexResponse = await fetch(BASE_URL + '/translated/index.json');
    var index = await indexResponse.json();

    var novelEntry = null;
    for (var i = 0; i < index.length; i++) {
      if (index[i].name === folderName) {
        novelEntry = index[i];
        break;
      }
    }

    if (!novelEntry) {
      return { path: folderName, url: folderName, name: folderName, chapters: [] };
    }

    var chapterFiles = novelEntry.files
      .filter(function(f) { return /^chapter\d+\.txt$/.test(f); })
      .sort(function(a, b) {
        var numA = parseInt(a.match(/\d+/)[0]);
        var numB = parseInt(b.match(/\d+/)[0]);
        return numA - numB;
      });

    var chapters = chapterFiles.map(function(file) {
      var chapterNum = parseInt(file.match(/\d+/)[0]);
      var chapterTitle = (metadata.chapter_titles && metadata.chapter_titles[chapterNum]) || ('Chapter ' + chapterNum);
      var chapterPath = folderName + '/' + file;

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
