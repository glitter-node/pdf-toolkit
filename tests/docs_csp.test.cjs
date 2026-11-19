const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'js', 'docs.js'), 'utf8');

function setup(fetch) {
  const nodes = new Map();
  let ready;
  const makeNode = tagName => ({tagName, children: [], textContent: '', append(...children) { this.children.push(...children); }});
  const status = makeNode('p');
  const list = makeNode('div');
  nodes.set('#docs-status', status);
  nodes.set('#docs-list', list);
  const document = {
    querySelector(selector) { return nodes.get(selector); },
    createElement: makeNode,
    addEventListener(name, callback) { if (name === 'DOMContentLoaded') ready = callback; }
  };
  vm.runInNewContext(source, {document, fetch});
  return {ready, status, list};
}

test('local docs render schema as text nodes', async () => {
  const requests = [];
  const view = setup(async (url, options) => {
    requests.push([url, options.credentials]);
    return {ok: true, json: async () => ({paths: {'/api/pdf/info': {post: {summary: '<img src=x onerror=alert(1)>', responses: {'200': {description: 'OK'}}}}}})};
  });
  await view.ready();
  assert.deepEqual(requests, [['/openapi.json', 'same-origin']]);
  assert.equal(view.status.textContent, '1 API operations available.');
  assert.equal(view.list.children.length, 1);
  assert.equal(view.list.children[0].children[1].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(view.list.children[0].children[2].children[1].textContent.includes('"200"'), true);
});

test('local docs show a safe error when schema loading fails', async () => {
  const view = setup(async () => ({ok: false}));
  await view.ready();
  assert.equal(view.status.textContent, 'Unable to load the API schema. Open the JSON link or try again.');
  assert.equal(view.list.children.length, 0);
});
