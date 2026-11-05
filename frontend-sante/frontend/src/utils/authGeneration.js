// An identity transition invalidates all pending profile/token responses.
let generation = 0;
export function getAuthGeneration() { return generation; }
export function invalidateAuthGeneration() { generation += 1; }

export function createProfileRequestGuard() {
  let sequence = 0;
  return () => {
    const request = ++sequence;
    const identity = getAuthGeneration();
    return () => request === sequence && identity === getAuthGeneration();
  };
}
