# Core associations - editable UML source

The specification uses fixed images for consistent layout. These three separate Mermaid diagrams provide editable source for the same associations.

## Original scope and reporting

```mermaid
classDiagram
direction LR
Project "1" --> "0..*" WorkOrder
WorkOrder "1" *-- "1..*" WorkOrderRevision
WorkOrderRevision "1" --> "0..*" ChangeEvent : original scope
```

## Versioned proposal and client decision

```mermaid
classDiagram
direction LR
ChangeOrder "1" *-- "1..*" ChangeOrderRevision
ChangeOrderRevision "1" --> "0..*" ApprovalRequest
ApprovalRequest "1" --> "0..1" ApprovalDecision
ApprovalDecision "0..1" --> "0..*" WorkAuthorization
```

Cross-view relationship: one ChangeEvent has zero or one ChangeOrder in the MVP.

## Asynchronous notification delivery

```mermaid
classDiagram
direction LR
ApprovalDecision ..> OutboxEvent : commits event
OutboxEvent "1" --> "0..*" Notification
Notification "1" --> "0..*" NotificationDelivery
```

The dashed dependency represents work performed by the approval service in the decision transaction. Notifications do not determine approval status.
