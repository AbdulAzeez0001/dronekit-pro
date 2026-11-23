# Structural-PCB kit — assembly model

The intended DroneKit Pro build model, recorded so board design stays
compatible with it. This is a SEPARATE design track from the electronic board.
Nothing here changes the electronic-board blocks in progress.

## Concept

The entire product is PCB. The airframe — frame, battery cage, prop guards,
stand — is not plastic or 3D-printed. It is a set of PCB panels that ship on one
fabrication sheet, snap out, click together into the 3D body, and are soldered
at the joints to lock rigid. The solder at these joints is STRUCTURAL (holding
FR4 panels together), not electrical.

Builder experience: snap panels off the sheet -> slot them together -> solder
the copper edge joints to make it firm -> mount the pre-assembled electronic
board. An iron is used, but only on the airframe joints, never on components.

One manufacturing process for the whole kit: PCB fab. No 3D printing, no
molding, no separate mechanical shop. This is the main advantage.

## Two tracks (keep separate)

1. Electronic board — the STM32/ESP32 flight controller. Fully factory-
   assembled by JLC (all SMD). Builder never solders a component. IN PROGRESS.
2. Structural PCB body — the airframe panels. A later design phase, started
   only after the electronic board outline, battery, and motor positions are
   fixed, because the panels are sized around them.

## How the structural body works

- Panelization: body panels + the main board are laid out on one large PCB
  panel, joined by break-tabs (mouse-bites or v-score). Builder snaps each out.
- Alignment: panels have cut slots + matching tabs so they self-align into the
  body shape before any solder ("click it in place").
- Structural joints: where two panels meet at an edge (e.g. a wall to the base
  at 90 deg), both edges carry exposed copper (castellations / solder tabs).
  The builder clicks them together and runs solder across the joint; the solder
  wets both panels' copper and forms a rigid bond.

## Design work this adds (later track)

- Mechanical design of how flat panels fold into a drone airframe: wall
  placement, joint geometry, how loads pass through the joints.
- Panelization layout: fit all body panels + the main board on one
  manufacturable sheet within the fab's max panel size.
- Board-outline + mounting reconciliation with the electronic board.

## Where the two tracks MUST meet (decide during board layout)

These are the only hard couplings, and getting them wrong means a finished body
won't accept the board. Fix them while the PCB is still being laid out:
- Board outline shape and size.
- Mounting hole positions + size (M2 vs M3) matching the frame standoffs/slots.
- Connector/switch placement: battery lead, motor connectors, boot switch, and
  any user-facing control must sit where the frame allows access.

## Open risk — vibration and impact durability

Honest flag. Structural-PCB kits are proven for slow tabletop robots (the
CircuitMess rover rolls). A DRONE vibrates hard and can crash. Soldered PCB-panel
joints and FR4 are brittle under sustained vibration and impact, so the airframe
durability is a real open question, not a given.

- Solder joints can fatigue-crack under motor vibration.
- FR4 panels can crack on impact.
- 1.6mm board may not be stiff enough for a drone frame; may need thicker board,
  reinforcement, or ribs.

Do not assume this works. Prototype the airframe early and stress/vibration-test
it before committing. If joints prove unreliable, fallbacks: screwed joints
through the panels, thicker FR4, or a hybrid (PCB body with a few mechanical
fasteners at high-stress joints).

## Status
- [ ] Electronic board finished + outline fixed (prerequisite for this track).
- [ ] Frame concept: how panels fold into the airframe.
- [ ] Panelization + break-tab plan.
- [ ] Structural joint method chosen (castellation solder vs screwed vs hybrid).
- [ ] Vibration/impact prototype tested before commit.
