#!/bin/bash
echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
echo

echo "=== queue (with start times + walltime) ==="
squeue -u dmullins -o "%.10i %.11P %.18j %.8T %.10M %.10l %.20R %.20S"
echo

echo "=== job details ==="
for j in $(squeue -u dmullins -h -o "%i"); do
  name=$(squeue -j $j -h -o "%j" 2>/dev/null)
  state=$(squeue -j $j -h -o "%T" 2>/dev/null)
  reason=$(squeue -j $j -h -o "%R" 2>/dev/null)
  start=$(squeue -j $j -h -o "%S" 2>/dev/null)
  dep=$(scontrol show job $j 2>/dev/null | grep -oP 'Dependency=\K\S+' | head -1)
  echo "  $j | $name | $state | reason=$reason | start=$start${dep:+ | dep=$dep}"
done
echo

echo "=== V3.1 download progress ==="
du -sh /ocean/projects/cis260106p/dmullins/models/DeepSeek-V3.1-Base 2>/dev/null || echo "(not started)"
shards=$(ls /ocean/projects/cis260106p/dmullins/models/DeepSeek-V3.1-Base/*.safetensors 2>/dev/null | wc -l)
echo "  shards on disk: ${shards}"
tail -n 1 /ocean/projects/cis260106p/dmullins/models/dl_v31.log 2>/dev/null | head -c 250
echo
echo

echo "=== sbatch outputs (last 3 most recent) ==="
ls -lt /ocean/projects/cis260106p/dmullins/minotaur/minotaur-*-*.out 2>/dev/null | head -3
echo

echo "=== generations per family ==="
for f in llama70b gemma31b deepseek_v4_flash; do
  latest=$(ls -t /ocean/projects/cis260106p/dmullins/minotaur/results/raw/$f/checkpoint_*.json 2>/dev/null | head -1)
  if [[ -n "$latest" ]]; then
    n=$(python -c "import json; print(len(json.load(open('$latest'))))" 2>/dev/null)
    echo "  $f: ${n} gens (latest ckpt: $(basename $latest))"
  else
    final=$(ls -t /ocean/projects/cis260106p/dmullins/minotaur/results/raw/$f/run_*.json 2>/dev/null | head -1)
    if [[ -n "$final" ]]; then
      n=$(python -c "import json; print(len(json.load(open('$final'))))" 2>/dev/null)
      echo "  $f: ${n} gens (FINISHED, run file: $(basename $final))"
    else
      echo "  $f: 0 gens"
    fi
  fi
done
