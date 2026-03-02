const fs = require('fs');
const path = require('path');

// Configuration
const TWITTER_ARCHIVE_PATH = 'C:/Users/Owner/twitter-archive-site';
const OUTPUT_PATH = 'C:/Users/Owner/Documents/transmissions11.github.io/paper-threads';
const TWEETS_FILE = path.join(TWITTER_ARCHIVE_PATH, 'data/tweets.js');
const MEDIA_SOURCE = path.join(TWITTER_ARCHIVE_PATH, 'data/tweets_media');

// Thread-of-threads root IDs
const INDEX_THREAD_IDS = [
  '1920202288678817885', // Original (May 2025)
  '1951357565797015944', // Second (Aug 2025)
  '1976660913353859136', // Latest (Oct 2025)
];

// Your user ID (for filtering self-replies)
const YOUR_USER_ID = '1022920763865812992';

console.log('Loading tweets...');

// Read and parse tweets.js
let tweetsRaw = fs.readFileSync(TWEETS_FILE, 'utf8');
// Remove the window.YTD.tweets.part0 = prefix
tweetsRaw = tweetsRaw.replace(/^window\.YTD\.tweets\.part0\s*=\s*/, '');
const tweetsArray = JSON.parse(tweetsRaw);

console.log(`Loaded ${tweetsArray.length} tweets`);

// Build tweet index by ID
const tweetsById = new Map();
for (const item of tweetsArray) {
  const tweet = item.tweet;
  tweetsById.set(tweet.id_str, tweet);
}

console.log('Built tweet index');

// Helper: Extract tweet ID from a t.co URL's expanded_url
function extractLinkedTweetId(tweet) {
  if (!tweet.entities?.urls) return null;
  for (const url of tweet.entities.urls) {
    const expanded = url.expanded_url || '';
    // Match x.com or twitter.com status URLs
    const match = expanded.match(/(?:x\.com|twitter\.com)\/\w+\/status\/(\d+)/);
    if (match) return match[1];
  }
  return null;
}

// Helper: Get all replies to a tweet (tweets where in_reply_to_status_id_str matches)
function getReplies(tweetId) {
  const replies = [];
  for (const [id, tweet] of tweetsById) {
    if (tweet.in_reply_to_status_id_str === tweetId &&
        tweet.in_reply_to_user_id_str === YOUR_USER_ID) {
      replies.push(tweet);
    }
  }
  return replies;
}

// Helper: Follow a reply chain (self-replies only)
function followReplyChain(startTweetId) {
  const chain = [];
  const startTweet = tweetsById.get(startTweetId);
  if (!startTweet) return chain;

  chain.push(startTweet);

  // Find all replies and follow the chain
  let currentId = startTweetId;
  const visited = new Set([currentId]);

  while (true) {
    const replies = getReplies(currentId);
    // Filter to self-replies we haven't visited
    const nextReplies = replies.filter(r => !visited.has(r.id_str));
    if (nextReplies.length === 0) break;

    // Sort by timestamp to get the immediate reply
    nextReplies.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    for (const reply of nextReplies) {
      if (!visited.has(reply.id_str)) {
        visited.add(reply.id_str);
        chain.push(reply);
        currentId = reply.id_str;
      }
    }
  }

  return chain;
}

// Helper: Extract media info from a tweet
function extractMedia(tweet) {
  const media = [];

  // Check extended_entities for media
  if (tweet.extended_entities?.media) {
    for (const m of tweet.extended_entities.media) {
      media.push({
        type: m.type,
        url: m.media_url_https || m.media_url,
        localFile: m.media_url_https ? path.basename(m.media_url_https) : null,
      });
    }
  }

  // Also check entities.media
  if (tweet.entities?.media) {
    for (const m of tweet.entities.media) {
      const existing = media.find(x => x.url === (m.media_url_https || m.media_url));
      if (!existing) {
        media.push({
          type: m.type,
          url: m.media_url_https || m.media_url,
          localFile: m.media_url_https ? path.basename(m.media_url_https) : null,
        });
      }
    }
  }

  return media;
}

// Helper: Find local media file for a tweet
function findLocalMediaFiles(tweetId) {
  const files = [];
  try {
    const mediaDir = fs.readdirSync(MEDIA_SOURCE);
    for (const file of mediaDir) {
      if (file.startsWith(tweetId + '-') || file.startsWith(tweetId + '_')) {
        files.push(file);
      }
    }
  } catch (e) {
    // Media dir might not exist
  }
  return files;
}

// Process a single tweet into our format
function processTweet(tweet) {
  const mediaFiles = findLocalMediaFiles(tweet.id_str);

  return {
    id: tweet.id_str,
    text: tweet.full_text,
    created_at: tweet.created_at,
    favorite_count: parseInt(tweet.favorite_count) || 0,
    retweet_count: parseInt(tweet.retweet_count) || 0,
    media: mediaFiles,
    urls: (tweet.entities?.urls || []).map(u => ({
      url: u.url,
      expanded_url: u.expanded_url,
      display_url: u.display_url,
    })),
  };
}

// Main extraction
console.log('Extracting thread-of-threads...');

const result = {
  extracted_at: new Date().toISOString(),
  index_threads: [],
  papers: [],
  all_media_files: new Set(),
};

// Process each index thread
for (const indexId of INDEX_THREAD_IDS) {
  console.log(`\nProcessing index thread ${indexId}...`);

  const indexTweet = tweetsById.get(indexId);
  if (!indexTweet) {
    console.log(`  WARNING: Index tweet ${indexId} not found`);
    continue;
  }

  const indexInfo = {
    id: indexId,
    text: indexTweet.full_text,
    created_at: indexTweet.created_at,
    paper_count: 0,
  };

  // Get all paper entries in this index's reply chain
  const paperEntries = followReplyChain(indexId);
  console.log(`  Found ${paperEntries.length} tweets in reply chain`);

  // Skip the first one (it's the index tweet itself)
  for (let i = 1; i < paperEntries.length; i++) {
    const entry = paperEntries[i];
    const linkedThreadId = extractLinkedTweetId(entry);

    if (!linkedThreadId) {
      console.log(`  Skipping entry ${entry.id_str} - no linked thread found`);
      continue;
    }

    // Extract paper info from the entry text
    const entryText = entry.full_text;

    // Get the detailed thread
    const detailedThread = followReplyChain(linkedThreadId);

    if (detailedThread.length === 0) {
      console.log(`  WARNING: Detailed thread ${linkedThreadId} not found in archive`);
      continue;
    }

    // Collect all media from the detailed thread
    const threadTweets = detailedThread.map(processTweet);
    const allMedia = [];
    for (const t of threadTweets) {
      for (const m of t.media) {
        allMedia.push(m);
        result.all_media_files.add(m);
      }
    }

    const paper = {
      entry_id: entry.id_str,
      entry_text: entryText,
      entry_date: entry.created_at,
      index_thread_id: indexId,
      detailed_thread_id: linkedThreadId,
      detailed_thread: threadTweets,
      media_files: allMedia,
    };

    result.papers.push(paper);
    indexInfo.paper_count++;
  }

  result.index_threads.push(indexInfo);
  console.log(`  Extracted ${indexInfo.paper_count} papers from this index`);
}

// Convert Set to Array for JSON
result.all_media_files = [...result.all_media_files];

console.log(`\n========================================`);
console.log(`Total papers extracted: ${result.papers.length}`);
console.log(`Total media files referenced: ${result.all_media_files.length}`);

// Write the JSON output
const outputFile = path.join(OUTPUT_PATH, 'papers.json');
fs.writeFileSync(outputFile, JSON.stringify(result, null, 2));
console.log(`\nWrote ${outputFile}`);

// Copy media files
console.log('\nCopying media files...');
const mediaDestDir = path.join(OUTPUT_PATH, 'media');
let copiedCount = 0;
let missingCount = 0;

for (const paper of result.papers) {
  for (const mediaFile of paper.media_files) {
    const srcPath = path.join(MEDIA_SOURCE, mediaFile);
    const destPath = path.join(mediaDestDir, mediaFile);

    if (fs.existsSync(srcPath)) {
      if (!fs.existsSync(destPath)) {
        fs.copyFileSync(srcPath, destPath);
        copiedCount++;
      }
    } else {
      missingCount++;
    }
  }
}

console.log(`Copied ${copiedCount} media files`);
if (missingCount > 0) {
  console.log(`${missingCount} media files not found in archive`);
}

console.log('\nDone!');
