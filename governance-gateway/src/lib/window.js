// rolling-window helpers
export function now() { return Date.now(); }
export function cutoff(ms) { return now() - ms; }
export function sweep(arr, winMs) {
  const c = cutoff(winMs);
  while (arr.length && arr[0] < c) arr.shift();
  return arr;
}