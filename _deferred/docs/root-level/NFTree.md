# NFTree

A token primitive for collective action with individual proof.

## The Pattern

One root. Many branches. Each branch bears fruit.

```
            Root Token
          (the collective)
                │
     ┌──────────┼──────────┐
     │          │          │
  Branch     Branch     Branch
(participant)(participant)(participant)
     │          │          │
     ▼          ▼          ▼
   Fruit      Fruit      Fruit
  (proof)    (proof)    (proof)
```

An NFTree begins with a single token representing something shared - a campaign, an event, a proposal, a creation. Participants receive branch tokens representing their stake in that shared thing. When the thing resolves, each branch bears fruit: a final token proving participation and outcome.

This is the structure underneath collective human action. It was always there. We just named it.

## Why Trees

Trees are how shared things become individual things.

A marathon is one event. Thousands run it. Each finishes with their own time, their own story. The race is the root. The runners are the branches. The medals are the fruit.

A crowdfunding campaign is one goal. Hundreds back it. Each pledged a different amount, for their own reasons. The campaign is the root. The pledges are the branches. The commemoratives are the fruit.

A DAO proposal is one decision. Members vote. Each cast their vote differently. The proposal is the root. The votes are the branches. The record is the fruit.

The tree captures what these have in common: collective participation that resolves into individual proof.

## The Three Stages

### Root (Genesis)

Something shared comes into existence:
- A campaign launches
- An event is announced
- A proposal is submitted
- A collaborative work begins

The root token defines what this thing is, what participation means, and how resolution happens. It's the seed that determines what kind of tree will grow.

### Branch (Participation)

Individuals attach themselves to the shared thing:
- A backer pledges funds
- An attendee claims a ticket
- A voter casts their vote
- A contributor adds their work

Each branch token represents one participant's stake. It's their connection to the root, their claim on the eventual fruit. Branches may be equal or weighted. They may be transferable or locked. The root defines the rules.

### Fruit (Resolution)

The shared thing completes, and individual outcomes crystallize:
- The race ends, times are recorded
- The campaign resolves, contributions finalized
- The vote closes, decisions made
- The work ships, credits assigned

Each branch bears exactly one fruit. The fruit token is permanent proof of participation and outcome. It contains the branch's relationship to the root and the final state of both.

Fruit is typically soulbound - it cannot be transferred because it represents something that happened to a specific participant. You can't sell your marathon finish. You can't trade your vote. The fruit is yours because the branch was yours.

## Properties

### Root Properties

```
Root {
  identity: what this collective thing is
  rules: how branches attach, grow, and fruit
  resolution: what triggers fruiting
  state: draft → active → resolved
}
```

### Branch Properties

```
Branch {
  root: which tree this belongs to
  holder: who owns this branch
  weight: how significant this participation is
  attachment: when and how they joined
  state: active → fruited
}
```

### Fruit Properties

```
Fruit {
  branch: which branch bore this
  root: which tree (inherited)
  holder: who owns this (same as branch holder)
  outcome: what happened
  proof: permanent record
  state: eternal
}
```

## Inheritance

Fruit inherits from both branch and root.

From the root, fruit inherits:
- The identity of the collective thing
- The context of what was shared
- The rules that governed participation

From the branch, fruit inherits:
- The participant's identity
- The weight of their participation
- The timestamp of their attachment

The fruit adds:
- The resolution state
- The individual outcome
- The proof of completion

This inheritance is what makes fruit meaningful. A marathon medal without the race is just metal. A commemorative without the campaign is just a token. The fruit carries the full history of root and branch.

## Implementations

NFTree is a pattern, not a protocol. Protocols implement the pattern for specific use cases.

### Pledge Protocol

Crowdfunding with milestone verification.

- **Root**: Campaign (goal, beneficiary, milestones)
- **Branch**: Pledge (backer, amount, conditions)
- **Fruit**: Commemorative (contribution, outcome, proof)

### Event Protocol

Ticketing with attendance proof.

- **Root**: Event (what, when, where)
- **Branch**: Ticket (attendee, tier, access)
- **Fruit**: Proof of Attendance (was there, timestamp, memories)

### Governance Protocol

Voting with permanent record.

- **Root**: Proposal (question, options, quorum)
- **Branch**: Vote (voter, choice, weight)
- **Fruit**: Vote Record (choice, outcome, participation proof)

### Collaboration Protocol

Collective creation with credit.

- **Root**: Project (what's being made, contributors, terms)
- **Branch**: Contribution (contributor, work, weight)
- **Fruit**: Credit (attribution, share, proof of involvement)

## Operations

### Plant

Create a root. Define what kind of tree this will be.

```
plant(identity, rules, resolution) → Root
```

### Attach

Add a branch to the tree. Connect a participant to the collective.

```
attach(root, participant, weight) → Branch
```

### Fruit

Resolve the tree. Transform all branches into fruit.

```
fruit(root, outcomes) → Fruit[]
```

### Prune (optional)

Remove a branch before fruiting. Detach a participant.

```
prune(branch) → void
```

### Graft (optional)

Transfer a branch to a different participant.

```
graft(branch, new_holder) → Branch
```

## Constraints

### One Root, Many Branches

A tree has exactly one root. Branches cannot exist without a root. The root defines the maximum number and type of branches.

### One Branch, One Fruit

Each branch bears exactly one fruit. Fruiting is irreversible. Once a branch has fruited, it cannot fruit again.

### Fruit Cannot Fall

Fruit is permanently attached to its holder. Soulbound by default. The proof cannot be separated from the participant.

### Trees Don't Merge

Two trees cannot combine into one. Each tree is its own lineage. Cross-tree relationships are references, not structural.

## NatLangChain Integration

NFTree is a native pattern in NatLangChain.

Every root is a NatLangChain contract declaring collective intent.

Every branch is a NatLangChain contract declaring individual commitment to that intent.

Every fruit is a NatLangChain artifact proving fulfillment of intent.

The tree structure maps directly to the intent → commitment → proof lifecycle that NatLangChain was built for.

```
NatLangChain Contract (Root):
  "This campaign exists to fund Sarah's marathon for charity."

NatLangChain Contract (Branch):  
  "I commit $2 per mile to support this campaign."

NatLangChain Artifact (Fruit):
  "This commitment was fulfilled: $52.40 contributed when Sarah completed 26.2 miles."
```

The prose is the program. The tree is the structure. Together they make collective action legible.

## The Discovery

This pattern wasn't invented. It was found.

We were building Pledge Protocol - crowdfunding with milestone verification. We noticed the structure: campaign → pledges → commemoratives. One to many to many, with transformation at each step.

Then we saw it everywhere. Events. Votes. Collaborations. The same shape underneath.

That shape is a tree. Root, branch, fruit.

We called it NFTree because it's an NFT that grows. One token becomes many. The tree is non-fungible because every tree is different. The branches are non-fungible because every participation is unique. The fruit is non-fungible because every outcome is individual.

NFTree: one root, many branches, each bears fruit.

The structure was always there. Now it has a name.

## License

[TBD]

## Part Of

NatLangChain Ecosystem
