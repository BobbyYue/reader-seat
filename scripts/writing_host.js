// Run through the host's code tool with the real tools object, not a model-written receipt.
// No Node or network dependency. All model choices inherit the calling host.
async function runWritingHost(tools, options) {
  const required = ['exec_command', 'write_stdin', 'multi_agent_v1__spawn_agent', 'multi_agent_v1__wait_agent', 'multi_agent_v1__close_agent'];
  for (const name of required) if (typeof tools[name] !== 'function') throw new Error('Required native host capability is unavailable: ' + name);
  const quote = value => "'" + String(value).replace(/'/g, "'\\''") + "'";
  const python = options.python || 'python3';
  const script = options.skillRoot + '/scripts/writing_host.py';
  const command = async (args, input) => {
    const parts = [python, '-B', script, ...args];
    let cmd = parts.map(quote).join(' ');
    if (input !== undefined) cmd = quote(python) + ' -c ' + quote('import subprocess,sys,termios; a=termios.tcgetattr(0); a[3]&=~(termios.ECHO|termios.ICANON); termios.tcsetattr(0,termios.TCSANOW,a); p=subprocess.run(sys.argv[1:],input=sys.stdin.readline(),text=True,capture_output=True); sys.stdout.write(p.stdout); sys.stderr.write(p.stderr); sys.exit(p.returncode)') + ' ' + cmd;
    let result = await tools.exec_command({cmd, tty: input !== undefined, yield_time_ms: 1000, max_output_tokens: 2000});
    let output = result.output || '';
    if (input !== undefined) {
      if (!result.session_id) throw new Error('Native bridge input channel failed');
      result = await tools.write_stdin({session_id: result.session_id, chars: JSON.stringify(input) + '\n', yield_time_ms: 1000, max_output_tokens: 2000});
      output += result.output || '';
    }
    while (result.session_id) {
      result = await tools.write_stdin({session_id: result.session_id, chars: '', yield_time_ms: 1000, max_output_tokens: 2000});
      output += result.output || '';
    }
    if (result.exit_code !== 0) throw new Error('Managed native bridge rejected the operation; inspect its private records');
    return JSON.parse(output);
  };
  const args = ['prepare', options.run, '--packets', options.packets];
  if (options.nativeRun) args.push('--native-run', options.nativeRun);
  const active = new Map();
  let failure = null;
  const review = async request => {
      const promptResult = await tools.exec_command({cmd: quote(python) + ' -c ' + quote('import pathlib,sys,json; print(json.dumps({"text":pathlib.Path(sys.argv[1]).read_text()}))') + ' ' + quote(request.prompt), max_output_tokens: 60000});
      if (promptResult.exit_code !== 0 || promptResult.original_token_count > 59000) throw new Error('Prepared review input could not be read completely');
      const spawnArguments = {fork_context: false, message: JSON.parse(promptResult.output).text};
      let spawn;
      if (request.status === 'started') {
        spawn = request.spawn;
      } else {
        if (request.status !== 'prepared') throw new Error('Uncertain prior launch; do not duplicate a possibly running reviewer');
        await command(['claim', options.run, '--request', request.attempt_id]);
        try { spawn = await tools.multi_agent_v1__spawn_agent(spawnArguments); }
        catch (error) {
          await command(['launch-failed', options.run, '--request', request.attempt_id],
                        {name: error.name || 'Error', message: String(error.message || error), code: error.code || null});
          throw new Error('Native launch failed without an agent receipt; inspect the saved error and confirm no agent exists before recover-launch');
        }
        await command(['started', options.run, '--request', request.attempt_id], spawn);
      }
      // No short polling: preserve the same live reviewer across timeout waits.
      let returned;
      let waits = 0;
      do {
        returned = await tools.multi_agent_v1__wait_agent({targets: [spawn.agent_id], timeout_ms: 120000});
      } while (returned.timed_out && ++waits < 3);
      if (returned.timed_out) throw new Error('Review is still running; resume the same stored agent instead of starting another');
      const raw = {arguments: spawnArguments, spawn, wait: returned};
      let imported;
      try { imported = await command(['finish', options.run, '--request', request.attempt_id], raw); }
      finally { await tools.multi_agent_v1__close_agent({target: spawn.agent_id}); }
      return imported;
  };
  try {
    for (;;) {
      if (!failure) {
        const batch = await command(args);
        if (batch.complete) {
          const remaining = await Promise.all(active.values());
          const failed = remaining.find(value => value.error);
          if (failed) throw failed.error;
          return {status: 'captured', round: batch.round, results: batch.results};
        }
        for (const request of batch.requests) {
          if (active.has(request.attempt_id)) continue;
          const result = review(request).then(
            value => ({id: request.attempt_id, value}),
            error => ({id: request.attempt_id, error})
          );
          active.set(request.attempt_id, result);
        }
      }
      if (!active.size) throw failure || new Error('No runnable request; native dependency or transport is blocked');
      // Release dependents after each collected return, not after the slowest peer.
      const completed = await Promise.race(active.values());
      active.delete(completed.id);
      if (completed.error) failure = failure || completed.error;
    }
  } catch (error) {
    await Promise.all(active.values());
    throw error;
  }
}
