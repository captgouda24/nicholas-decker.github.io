const fs = require('fs');
const path = require('path');

const INPUT = 'C:/Users/Owner/Documents/transmissions11.github.io/paper-threads/papers.json';
const OUTPUT = 'C:/Users/Owner/Documents/transmissions11.github.io/paper-threads/papers-indexed.json';

const data = JSON.parse(fs.readFileSync(INPUT, 'utf8'));

// Parse author and year from entry_text
// Examples:
// "Krugman (1980) "Scale Economies..."
// "Berry and Waldfogel, "Do Mergers..." (2001)"
// "Madestam, Shoag, Veuger, Yanigazawa-Drott, "Do Political Protests Matter?" (2011)"
// "Acemoglu, "Technical Change, Inequality, and the Labor Market" (2002)"

function parseEntry(entryText) {
  // Clean up the text
  let text = entryText.replace(/\n/g, ' ').replace(/https?:\/\/\S+/g, '').trim();

  // Try to extract year - look for (YYYY) pattern
  const yearMatch = text.match(/\((\d{4})\)/);
  const year = yearMatch ? parseInt(yearMatch[1]) : null;

  // Extract authors - everything before the first quote or (year)
  let authorPart = text;

  // Find where title starts (first quotation mark)
  const quoteIndex = text.search(/[""\"]/);
  if (quoteIndex > 0) {
    authorPart = text.substring(0, quoteIndex).trim();
  }

  // Remove trailing comma, "and", year in parens
  authorPart = authorPart
    .replace(/\(\d{4}\)/g, '')
    .replace(/,\s*$/, '')
    .trim();

  // Extract title - text between quotes
  const titleMatch = text.match(/[""\""]([^"""\"]+)[""\"\"]/);
  const title = titleMatch ? titleMatch[1].trim() : '';

  // Parse first author
  // Format is LAST NAMES only: "Krugman", "Berry and Waldfogel", "Madestam, Shoag, Veuger..."
  // In "x and y" format, x is the last name of first author, y is last name of second
  let firstAuthor = authorPart;
  let sortName = '';

  // If there's a comma, first author (last name) is before the comma
  if (authorPart.includes(',')) {
    firstAuthor = authorPart.split(',')[0].trim();
    // firstAuthor is already just the last name, use it directly for sorting
    sortName = firstAuthor.toLowerCase().replace(/[^a-z]/g, '');
  }
  // If there's "and" but no comma, first author is before "and"
  else if (authorPart.toLowerCase().includes(' and ')) {
    firstAuthor = authorPart.split(/ and /i)[0].trim();
    // firstAuthor is already just the last name, use it directly for sorting
    sortName = firstAuthor.toLowerCase().replace(/[^a-z]/g, '');
  }
  // Single author - just a last name
  else {
    sortName = firstAuthor.toLowerCase().replace(/[^a-z]/g, '');
  }

  // Fallback if sortName is empty
  if (!sortName) sortName = 'unknown';

  return {
    authors: authorPart,
    firstAuthor: firstAuthor,
    sortName: sortName,
    title: title,
    year: year,
  };
}

// Process all papers
const processedPapers = data.papers.map((paper, idx) => {
  const parsed = parseEntry(paper.entry_text);

  return {
    id: idx,
    entryId: paper.entry_id,
    threadId: paper.detailed_thread_id,
    authors: parsed.authors,
    firstAuthor: parsed.firstAuthor,
    sortName: parsed.sortName,
    title: parsed.title,
    year: parsed.year,
    entryDate: paper.entry_date,
    threadLength: paper.detailed_thread.length,
    mediaCount: paper.media_files.length,
    thread: paper.detailed_thread,
    mediaFiles: paper.media_files,
  };
});

// Sort by author
const byAuthor = [...processedPapers].sort((a, b) => {
  const cmp = a.sortName.localeCompare(b.sortName);
  if (cmp !== 0) return cmp;
  return (a.year || 0) - (b.year || 0);
});

// Sort by year
const byYear = [...processedPapers].sort((a, b) => {
  const cmp = (b.year || 0) - (a.year || 0); // Newest first
  if (cmp !== 0) return cmp;
  return a.sortName.localeCompare(b.sortName);
});

// Group by author letter
const authorGroups = {};
for (const p of byAuthor) {
  const letter = (p.sortName && p.sortName[0]) ? p.sortName[0].toUpperCase() : '?';
  if (!authorGroups[letter]) authorGroups[letter] = [];
  authorGroups[letter].push(p.id);
}

// Group by decade
const yearGroups = {};
for (const p of byYear) {
  if (!p.year) {
    if (!yearGroups['Unknown']) yearGroups['Unknown'] = [];
    yearGroups['Unknown'].push(p.id);
  } else {
    const decade = Math.floor(p.year / 10) * 10 + 's';
    if (!yearGroups[decade]) yearGroups[decade] = [];
    yearGroups[decade].push(p.id);
  }
}

const output = {
  papers: processedPapers,
  byAuthorOrder: byAuthor.map(p => p.id),
  byYearOrder: byYear.map(p => p.id),
  authorGroups: authorGroups,
  yearGroups: yearGroups,
  stats: {
    totalPapers: processedPapers.length,
    totalTweets: processedPapers.reduce((sum, p) => sum + p.threadLength, 0),
    totalImages: processedPapers.reduce((sum, p) => sum + p.mediaCount, 0),
    yearRange: {
      min: Math.min(...processedPapers.filter(p => p.year).map(p => p.year)),
      max: Math.max(...processedPapers.filter(p => p.year).map(p => p.year)),
    }
  }
};

fs.writeFileSync(OUTPUT, JSON.stringify(output, null, 2));
console.log('Built index with', processedPapers.length, 'papers');
console.log('Year range:', output.stats.yearRange.min, '-', output.stats.yearRange.max);
console.log('Author groups:', Object.keys(authorGroups).sort().join(', '));
console.log('Year groups:', Object.keys(yearGroups).join(', '));
