---
name: hermes-container-spike
description: Use when inspecting, configuring, mounting files into, or testing the ready-made Hermes Docker image during stage 0. Never build or mutate the image.
---

# Hermes container capability spike

## Hard constraints

- Use the existing ready-made Hermes image.
- Do not create a Dockerfile for Hermes.
- Do not run docker build or docker compose build for Hermes.
- Do not use docker cp.
- Do not use docker commit.
- Do not install packages inside the container.
- Do not edit files inside the container.
- Do not create production code based on guessed Hermes APIs.

## Allowed mechanisms

- docker compose pull;
- docker compose config;
- docker compose ps;
- docker compose logs;
- docker image inspect;
- docker container inspect;
- read-only diagnostic docker compose exec;
- bind mounts declared in compose;
- named volumes declared in compose;
- editing host files;
- restarting or recreating the service after approval.

## Investigation sequence

1. Locate the active compose project.
2. Record the image name, tag and digest.
3. Record container user, HOME, working directory and command.
4. Run Hermes version and help commands.
5. Discover actual configuration, plugin, skill and state paths.
6. Classify each path as:
   - read-only project input;
   - read-write runtime state;
   - secret;
   - unknown.
7. Test a neutral read-only bind mount.
8. Test plugin discovery using a host-mounted probe.
9. Test tools, hooks, toolsets and session identifiers.
10. Record evidence for every conclusion.

## Evidence requirements

Every finding must include at least one of:

- exact command;
- relevant output excerpt without secrets;
- file path inside the image;
- Hermes help output;
- source-code location;
- reproducible test.

Never mark an item PASS based only on documentation.

## Output

Update:

- docs/experiments/hermes-container-baseline.md
- docs/experiments/hermes-capability-spike.md
- docs/decisions/open-questions.md

Report unknown capabilities rather than inventing an adapter.
