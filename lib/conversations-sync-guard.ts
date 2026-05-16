/**
 * Guards against accidental chat/project loss when the server returns an empty list
 * (misconfigured backend, Firestore outage, wrong user id) but the browser still has data.
 */

export type TimestampedItem = { id: string; updatedAt?: Date }

/**
 * Merge local + remote by id. Remote wins on conflicts when both sides have the id.
 *
 * When remote is empty but local is not, keep local items (do not treat as "deleted on server").
 * When both are non-empty, local-only ids are dropped (deletion synced from another device).
 */
export function mergeByTimestampSafe<T extends TimestampedItem>(
  local: T[],
  remote: T[]
): T[] {
  if (remote.length === 0 && local.length > 0) {
    return sortByUpdatedAtDesc([...local])
  }

  const map = new Map<string, T>()
  const remoteIds = new Set(remote.map((item) => item.id))

  for (const item of remote) {
    map.set(item.id, item)
  }

  for (const localItem of local) {
    if (!remoteIds.has(localItem.id)) {
      continue
    }

    const remoteItem = map.get(localItem.id)
    if (remoteItem && localItem.updatedAt && remoteItem.updatedAt) {
      const localTime = new Date(localItem.updatedAt).getTime()
      const remoteTime = new Date(remoteItem.updatedAt).getTime()
      if (localTime > remoteTime) {
        map.set(localItem.id, localItem)
      }
    }
  }

  return sortByUpdatedAtDesc(Array.from(map.values()))
}

/**
 * Block a full "sync" that would wipe server data: empty payload while we know the
 * server previously had items for this session.
 */
export function shouldBlockDestructiveEmptySync(
  payloadCount: number,
  lastKnownServerCount: number | null
): boolean {
  if (payloadCount > 0) {
    return false
  }
  return lastKnownServerCount !== null && lastKnownServerCount > 0
}

function sortByUpdatedAtDesc<T extends TimestampedItem>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const aTime = a.updatedAt ? new Date(a.updatedAt).getTime() : 0
    const bTime = b.updatedAt ? new Date(b.updatedAt).getTime() : 0
    return bTime - aTime
  })
}
