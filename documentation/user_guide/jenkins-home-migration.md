# Jenkins home persistence and existing-installation migration

The Jenkins image uses `/var/jenkins_home`. The service must mount its named
`jenkins_home` volume there. Older configuration mounted that volume at
`/var/lib/jenkins`, leaving the actual home in an anonymous Docker volume.
Updating the compose file alone does not migrate an existing installation.

## Before changing an existing service

Use the live-operation approval boundary and identify the actual service,
node, task, container, home directory and both volume identities. Inspect the
running image's `JENKINS_HOME`; do not infer it from a volume name. A running
container or successful login does not establish persisted job integrity.

Treat the currently active home as the migration source only after its
ownership is established. If another volume contains data, do not overwrite or
merge it automatically. Retain older volumes for separate recovery assessment.
Migrating the current home does not recover previously lost jobs.

1. Verify sufficient disk space and a protected backup directory. Backups and
   service specifications contain credentials; restrict access and exclude
   them from Git, public evidence and ordinary diagnostic output.
2. Record the exact source volume and service specification. Retain a reference
   to an anonymous source volume so task replacement cannot remove it.
3. Put Jenkins into quiet mode through its authenticated API. Confirm no busy
   executors or running builds, and exclude concurrent configuration changes.
4. Capture a consistent backup of the active home and destination. Verify the
   archives. A brief container pause may be used only with a stable task and
   guaranteed unpause on failure; prolonged pauses risk Swarm replacement.
5. Copy into a verified empty destination, preserving ownership, permissions,
   symlinks and file contents. Compare the complete trees while the source is
   stable. Record equality and counts, never credential values or fingerprints.
6. Update only the Jenkins service so the named volume targets
   `/var/jenkins_home`. Do not run old and new Jenkins processes concurrently
   against that home. Keep quiet mode and exclusion of configuration changes
   in effect through cutover. Comparison establishes equality at capture;
   unpause can permit background writes. Recheck the retained source against
   the capture and resolve subsequent changes before claiming lossless cutover.
   Synchronize the repository compose configuration.
7. Verify the resulting mount, authenticated API access and expected jobs/data.
   Leave quiet mode when ready. A controlled task replacement should reuse the
   same named volume and retain a harmless persistence probe.
8. Retain protected backups and the old source until recovery acceptance is
   complete. Do not prune volumes as part of this migration.

## Rollback

If the migrated service has accepted writes, quiesce and back up its current
state before rollback. Restore the **exact retained source volume** at
`/var/jenkins_home`, with the compatible image/configuration and one writer.
Reverting the old `/var/lib/jenkins` mount or blindly running service rollback
can create another empty anonymous home; neither is a data-preserving rollback.

Stop on ambiguous data ownership, a nonempty destination, unstable task
identity, failed backup/copy verification, or unavailable recovery material.
