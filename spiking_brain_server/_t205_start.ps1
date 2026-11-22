$repoRoot = if ($env:Q_SPEACE_WSL_REPO_ROOT) { $env:Q_SPEACE_WSL_REPO_ROOT } else { (wsl.exe -d Ubuntu -- wslpath -a (Split-Path -Parent $PSScriptRoot)).Trim() }
$modelPath = if ($env:Q_SPEACE_INSTRUCT_MODEL_PATH) { $env:Q_SPEACE_INSTRUCT_MODEL_PATH } else { '$HOME/models/qwen2.5-3b-instruct' }
$instructionCmd = "cd '$repoRoot' && source ~/.venvs/spikingbrain/bin/activate && export Q_SPEACE_INSTRUCT_MODEL_PATH=""$modelPath"" && export Q_SPEACE_INSTRUCT_PORT=8002 && export Q_SPEACE_INSTRUCT_MAX_NEW_TOKENS=256 && python -m spiking_brain_server.instruction_server > /tmp/q_speace_instruction.log 2>&1"
Start-Process -FilePath wsl.exe -ArgumentList @('-d','Ubuntu','--','bash','-lc',$instructionCmd) -WindowStyle Hidden
'sidecar start requested'