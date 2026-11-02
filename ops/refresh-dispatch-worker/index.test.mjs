import test from 'node:test';
import assert from 'node:assert/strict';
import { freshnessCutoff, isFresh, isLateWindow, refreshTarget, runCheck, TARGETS } from './index.mjs';

const early = new Date('2026-11-01T00:00:00Z'); // 05:30 IST
const target = TARGETS[0];

function mockGithub(date = null, status = 204) {
  const calls = [];
  async function request(url, options = {}) {
    calls.push({ url, options });
    if (url.includes('/commits?')) return { ok: true, status: 200, json: async () =>
      date ? [{ commit: { committer: { date } } }] : [] };
    if (url.includes('/dispatches')) return { ok: status === 204, status };
    throw new Error('Unexpected URL: ' + url);
  }
  return { calls, request };
}

test('IST day and freshness cutoff handle UTC day rollover', () => {
  assert.equal(new Date(freshnessCutoff(early)).toISOString(), '2026-10-31T23:30:00.000Z');
  assert.equal(new Date(freshnessCutoff(new Date('2026-10-31T18:20:00Z'))).toISOString(),
    '2026-10-30T23:30:00.000Z');
  assert.equal(new Date(freshnessCutoff(new Date('2026-10-31T18:30:00Z'))).toISOString(),
    '2026-10-31T23:30:00.000Z');
});

test('fresh feed skips dispatch; stale feed dispatches to main', async () => {
  const fresh = mockGithub('2026-10-31T23:40:00Z');
  assert.equal((await refreshTarget(target, {GITHUB_TOKEN:'TEST'}, early, fresh.request)).status, 'fresh');
  assert.equal(fresh.calls.length, 1);
  const stale = mockGithub('2026-10-31T23:29:00Z');
  assert.equal((await refreshTarget(target, {GITHUB_TOKEN:'TEST'}, early, stale.request)).status, 'dispatched');
  assert.equal(stale.calls.length, 2);
  assert.equal(JSON.parse(stale.calls[1].options.body).ref, 'main');
  assert.equal(stale.calls[1].options.headers.Authorization, 'Bearer TEST');
});

test('GitHub freshness check failure retries; denied workflow dispatch errors', async () => {
  const calls = [];
  const request = async url => {
    calls.push(url);
    return url.includes('/commits?') ? {ok:false, status:503} : {status:403};
  };
  await assert.rejects(() => refreshTarget(target, {GITHUB_TOKEN:'TEST'}, early, request), /HTTP 403/);
  assert.equal(calls.length, 2);
  await assert.rejects(() => refreshTarget(target, {}, early, request), /Missing GITHUB_TOKEN/);
});

test('late alert window is triggered at exactly 06:40 IST', () => {
  assert.equal(isLateWindow(new Date('2026-11-01T01:09:59Z')), false);
  assert.equal(isLateWindow(new Date('2026-11-01T01:10:00Z')), true);
  assert.equal(isFresh('2026-10-31T23:40:00Z', early), true);
});

test('both repositories dispatch, and late checks generate an alert', async () => {
  const calls = [];
  const request = async (url, opts = {}) => {
    calls.push({url, opts});
    if (url.includes('/commits?')) return {ok:true, status:200, json:async()=>[]};
    if (url.includes('/dispatches')) return {ok:true, status:204};
    if (url === 'https://alerts.example/hook') return {ok:true,status:200};
    throw new Error('Unexpected URL');
  };
  const env = {GITHUB_TOKEN:'TEST', ALERT_WEBHOOK_URL:'https://alerts.example/hook'};
  const first = await runCheck(env, early, request);
  assert.equal(first.length, 2);
  assert.equal(first.every(x => x.status === 'dispatched'), true);
  assert.equal(calls.filter(x => x.url.includes('/dispatches')).length, 2);
  assert.equal(calls.filter(x => x.url.includes('alerts.example')).length, 0);
  await runCheck(env, new Date('2026-11-01T01:10:00Z'), request);
  const alerts = calls.filter(x => x.url.includes('alerts.example'));
  assert.equal(alerts.length, 1);
  assert.match(JSON.parse(alerts[0].opts.body).text, /needs attention/);
});
