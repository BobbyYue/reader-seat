// Offline protocol regression. These tool returns are synthetic, not model evidence.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const scope = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../scripts/writing_host.js'), 'utf8'), scope);

async function probe(rejectSpawn, alreadyStarted = false) {
  let state = alreadyStarted ? 'started' : 'prepared', pending = null, split = false, spawned = 0, closed = 0, done = false;
  const answer = value => ({output: JSON.stringify(value), exit_code: 0});
  const tools = {
    async exec_command({cmd}) {
      if (cmd.includes("'prepare'")) return answer({round: 1, complete: done, results: done ? {reader: '/synthetic/result.json'} : {},
        requests: done ? [] : [{role: 'reader', attempt_id: 'fixture', status: state, prompt: '/synthetic/prompt',
          spawn: state === 'started' ? {agent_id: 'actual-fixture-agent'} : null}]});
      if (cmd.includes("'claim'")) {
        state = 'launching'; split = true;
        return {output: '{"status":"launching"}', session_id: 1};
      }
      for (const name of ['started', 'finish', 'launch-failed']) {
        if (cmd.includes("'" + name + "'")) { pending = name; return {output: '', session_id: 2}; }
      }
      return answer({text: 'Synthetic isolated prompt'});
    },
    async write_stdin({chars}) {
      if (split) { split = false; return {output: '', exit_code: 0}; }
      const value = JSON.parse(chars);
      if (pending === 'started') { assert.equal(value.agent_id, 'actual-fixture-agent'); state = 'started'; }
      if (pending === 'finish') { assert.equal(value.arguments.fork_context, false); done = true; state = 'captured'; }
      if (pending === 'launch-failed') state = 'launch-uncertain';
      pending = null;
      return answer({status: state});
    },
    async multi_agent_v1__spawn_agent(args) {
      assert.equal(args.fork_context, false); spawned++;
      if (rejectSpawn) throw new Error('SYNTHETIC rejection with no receipt');
      return {agent_id: 'actual-fixture-agent', nickname: 'Fixture'};
    },
    async multi_agent_v1__wait_agent() {
      return {status: {'actual-fixture-agent': {completed: '{"verdict":"pass"}'}}, timed_out: false};
    },
    async multi_agent_v1__close_agent() { closed++; return {}; }
  };
  const options = {skillRoot: '/synthetic/skill', run: '/synthetic/run', packets: '/synthetic/packets'};
  if (rejectSpawn) {
    await assert.rejects(scope.runWritingHost(tools, options), /confirm no agent/);
    assert.equal(state, 'launch-uncertain');
    await assert.rejects(scope.runWritingHost(tools, options), /Uncertain prior launch/);
    assert.equal(spawned, 1);
  } else {
    const result = await scope.runWritingHost(tools, options);
    assert.equal(result.status, 'captured');
    assert.equal(spawned, alreadyStarted ? 0 : 1); assert.equal(closed, 1);
  }
}

async function dependencyProbe() {
  const roles = ['no-context', 'readability', 'structure-visual', 'source-reliability'];
  const jobs = Object.fromEntries(roles.map(role => [role, {role, attempt_id: role, status: 'prepared', prompt: '/fixture/' + role}]));
  const events = [], sessions = new Map(), launches = {};
  let serial = 100, release;
  const sourceStarted = new Promise(resolve => { release = resolve; });
  const answer = value => ({output: JSON.stringify(value), exit_code: 0});
  const tools = {
    async exec_command({cmd}) {
      if (cmd.includes("'prepare'")) {
        const complete = roles.every(role => jobs[role].status === 'captured');
        const requests = roles.filter(role => jobs[role].status !== 'captured' &&
          (role !== 'source-reliability' || jobs['no-context'].status === 'captured')).map(role => jobs[role]);
        return answer({round: 1, complete, requests, results: {}});
      }
      const operation = ['claim', 'started', 'finish', 'launch-failed'].find(name => cmd.includes("'" + name + "'"));
      if (operation) {
        const role = cmd.match(/'--request'\s+'([^']+)'/)[1];
        if (operation === 'claim') {
          assert.equal(jobs[role].status, 'prepared'); jobs[role].status = 'launching'; return answer({});
        }
        const id = serial++; sessions.set(id, {operation, role});
        return {output: '', session_id: id};
      }
      const role = roles.find(role => cmd.includes('/fixture/' + role));
      assert.ok(role); return answer({text: 'ROLE:' + role});
    },
    async write_stdin({session_id, chars}) {
      const {operation, role} = sessions.get(session_id);
      sessions.delete(session_id);
      const value = JSON.parse(chars);
      if (operation === 'started') { jobs[role].status = 'started'; jobs[role].spawn = value; }
      if (operation === 'finish') { jobs[role].status = 'captured'; events.push('captured:' + role); }
      return answer({});
    },
    async multi_agent_v1__spawn_agent(args) {
      assert.equal(args.fork_context, false);
      const role = args.message.slice(5);
      launches[role] = (launches[role] || 0) + 1;
      events.push('started:' + role);
      if (role === 'source-reliability') release();
      return {agent_id: role};
    },
    async multi_agent_v1__wait_agent({targets}) {
      const role = targets[0];
      if (role === 'readability' || role === 'structure-visual') await sourceStarted;
      return {status: {[role]: {completed: '{"status":"pass"}'}}, timed_out: false};
    },
    async multi_agent_v1__close_agent({target}) { events.push('closed:' + target); return {}; }
  };
  let timer;
  try {
    const timedOut = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Dependency scheduler stalled behind unrelated reviewers')), 5000); });
    await Promise.race([scope.runWritingHost(tools, {skillRoot: '/fixture/skill', run: '/fixture/run', packets: '/fixture/packets'}), timedOut]);
  } finally { clearTimeout(timer); }
  assert.ok(events.indexOf('started:source-reliability') < events.indexOf('captured:structure-visual'));
  assert.ok(events.indexOf('captured:no-context') < events.indexOf('started:source-reliability'));
  assert.deepEqual(Object.values(launches), [1, 1, 1, 1]);
  assert.equal(events.filter(event => event.startsWith('closed:')).length, 4);
}

(async () => {
  await probe(false);
  await probe(true);
  await probe(false, true);
  await dependencyProbe();
  process.stdout.write('PASS: split-output, native capture, uncertain launch, resume without respawn, immediate dependency scheduling and complete cleanup\n');
})().catch(error => { process.stderr.write(String(error.stack)); process.exitCode = 1; });
