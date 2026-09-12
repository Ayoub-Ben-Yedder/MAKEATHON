# Automated FIFO Inventory Management and XY Robotic Shelf System

## 1. System Overview

The proposed system is an **automated inventory management system integrated with an XY robotic shelf-access mechanism**.

Its purpose is to automatically:

1. Identify incoming products.
2. Determine their quantity using weight measurement.
3. Associate products with physical boxes.
4. Assign boxes to available shelf cells.
5. Record the exact storage location `(X, Y)`.
6. Track how long each box has been stored.
7. Prevent products from being retrieved before they have been stored for **24 hours**.
8. Apply **FIFO (First-In, First-Out)** inventory management.
9. Determine which boxes should be retrieved for a requested quantity.
10. Command the XY robotic mechanism to access the required cells.
11. Update the inventory after successful storage or retrieval.

The system consists of a **web-based user interface**, a **Flask backend**, a **database**, product-identification and weight-measurement components, and an **ESP32-controlled XY robotic mechanism**.

---

# 2. Overall Architecture

The system can be divided into five major layers:

```text
┌─────────────────────────────────────────────┐
│              WEB APPLICATION                │
│         HTML / CSS / JavaScript             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                FLASK SERVER                 │
│                                             │
│ Inventory │ FIFO │ 24h Rule │ Robot Control │
└───────────────┬─────────────────┬───────────┘
                │                 │
                ▼                 ▼
        ┌──────────────┐    ┌──────────────┐
        │   DATABASE   │    │    ESP32     │
        │              │    │              │
        │ Products     │    │ Motor Ctrl.  │
        │ Boxes        │    │ Sensors      │
        │ Cells        │    │ Actuators    │
        └──────────────┘    └──────┬───────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │ XY ROBOTIC SHELF │
                         └──────────────────┘
```

---

# 3. Physical System

The physical part consists primarily of a **shelving structure divided into cells**.

Each cell has a unique coordinate:

```text
          X →
       0    1    2    3    4

Y 0   [ ]  [ ]  [ ]  [ ]  [ ]

↓ 1   [ ]  [ ]  [ ]  [ ]  [ ]

  2   [ ]  [ ]  [ ]  [ ]  [ ]

  3   [ ]  [ ]  [ ]  [ ]  [ ]
```

The XY mechanism can move horizontally and vertically to reach a particular cell.

For example:

```text
Cell ID = 17
X = 3
Y = 2
```

means the robot must move to coordinate:

```text
X3, Y2
```

The cell itself can contain **more than one physical box**, depending on its capacity.

---

# 4. Product Identification

When new products arrive, the system needs to determine what type of product has been introduced.

A camera can capture an image of the incoming product.

The image is processed by the product-identification component, which determines the product type.

The resulting information is sent to Flask.

Conceptually:

```text
Product
   │
   ▼
Camera
   │
   ▼
Image
   │
   ▼
Product Identification
   │
   ▼
Product ID
   │
   ▼
Flask
```

For example:

```text
Detected product:
Product A

Confidence:
96%
```

The identification system does not need to directly control the robot. It provides Flask with information that Flask uses for inventory management.

---

# 5. Quantity Determination

The system can use a **load cell** to determine the quantity of products entering a box.

Suppose one product weighs:

```text
100 g
```

and the measured contents weigh:

```text
1500 g
```

The system can estimate:

```text
1500 / 100 = 15 products
```

Therefore:

```text
Quantity = 15
```

The product's expected weight can be stored in the `Products` table.

For example:

```text
Product A
Weight dry = 100 g
Weight wet = 110 g
```

The exact calculation can later be adapted depending on the physical characteristics of your products.

---

# 6. Box Management

A major part of your system is the concept of a **box**.

A product and a box are not the same thing.

A product represents a type of item:

```text
Product A
```

while a box represents a **physical batch/container of that product**:

```text
Box #101
Product A
Quantity: 20
Stored: September 10, 08:00
Location: X2,Y4
```

This distinction is essential for implementing FIFO correctly.

---

# 7. Database Structure

The database consists of three primary entities.

## Products

```text
Products
----------------
id
name
weight_dry
weight_wet
```

A product represents a particular type of inventory item.

---

## Cells

```text
Cells
----------------
id
x
y
capacity
```

A cell represents a physical location in the robotic shelf.

The combination of `x` and `y` uniquely identifies the physical position.

For example:

```text
Cell #12
X = 3
Y = 5
Capacity = 4 boxes
```

---

## Boxes

```text
Boxes
----------------
id
product_id
cell_id
quantity
added_at
```

A box connects the product to its physical location.

For example:

```text
Box #105
Product ID = 3
Cell ID = 12
Quantity = 20
Added at = September 10, 08:30
```

The `added_at` field is particularly important because it determines when the box becomes eligible for retrieval.

---

# 8. 24-Hour Storage Rule

Every box must remain in the shelf for **at least 24 hours** before its contents can be retrieved.

The system therefore calculates:

```text
Ready time = added_at + 24 hours
```

For example:

```text
Box stored:
September 10, 08:00

Ready:
September 11, 08:00
```

Before that time:

```text
Status = WAITING
```

After that time:

```text
Status = READY
```

The system should never allow a normal retrieval operation to select a box whose 24-hour storage period has not elapsed.

---

# 9. FIFO Inventory Management

FIFO means:

> **First In, First Out**

The oldest eligible inventory must be retrieved before newer eligible inventory.

Suppose the database contains:

| Box  | Product | Quantity | Stored       | Status  |
| ---- | ------- | -------: | ------------ | ------- |
| #101 | A       |       20 | 3 days ago   | READY   |
| #105 | A       |       15 | 2 days ago   | READY   |
| #108 | A       |       20 | 12 hours ago | WAITING |
| #112 | A       |       10 | 1 day ago    | READY   |

If the user requests:

```text
30 × Product A
```

the system must select:

```text
Box #101 → 20
Box #112 → 10
```

It must **not** select Box #108 because it has not reached the 24-hour requirement.

The effective selection order is therefore:

```text
Filter by product
        ↓
Remove empty boxes
        ↓
Remove boxes younger than 24 hours
        ↓
Sort by added_at ASC
        ↓
Select oldest boxes
        ↓
Continue until requested quantity is satisfied
```

---

# 10. Partial Box Retrieval

FIFO does not mean that an entire box must always be removed.

Suppose:

```text
Box #101
Quantity = 20
```

and the user requests:

```text
5
```

The system retrieves:

```text
5
```

and updates the box to:

```text
Quantity = 15
```

The original `added_at` remains associated with that box.

This is important because the remaining 15 products are still part of the same physical box and have already satisfied the 24-hour requirement.

---

# 11. Multiple Boxes in One Cell

A cell can contain multiple boxes.

For example:

```text
Cell X3,Y2

┌─────────────────────┐
│ Box #101            │
│ Product A — 20      │
│                     │
│ Box #108            │
│ Product A — 15      │
│                     │
│ Box #114            │
│ Product B — 10      │
└─────────────────────┘
```

This means the database cannot simply store:

```text
Cell → Product → Quantity
```

because that would lose information about individual boxes.

Instead:

```text
Cell
 ├── Box #101
 ├── Box #108
 └── Box #114
```

Each box has its own:

* product
* quantity
* storage time
* ID

This allows the FIFO algorithm to operate correctly.

---

# 12. Storage Process

When a new box arrives, the process is:

```text
                New Box
                   │
                   ▼
              Capture Image
                   │
                   ▼
           Identify Product
                   │
                   ▼
             Measure Weight
                   │
                   ▼
          Calculate Quantity
                   │
                   ▼
             Flask Backend
                   │
                   ▼
         Find Suitable Cell
                   │
                   ▼
              Assign X,Y
                   │
                   ▼
             Send Command
                   │
                   ▼
                ESP32
                   │
                   ▼
             XY Movement
                   │
                   ▼
           Place Box in Cell
                   │
                   ▼
        Confirm Successful Storage
                   │
                   ▼
          Create Box in Database
                   │
                   ▼
             Start 24h Timer
```

The **storage timestamp should be created when the robot successfully stores the box**, rather than when the operator first starts the process.

---

# 13. Retrieval Process

The retrieval process is:

```text
User requests product
        │
        ▼
Select quantity
        │
        ▼
Flask queries database
        │
        ▼
Find matching product
        │
        ▼
Check quantity
        │
        ▼
Check 24-hour requirement
        │
        ▼
Sort boxes by added_at
        │
        ▼
FIFO retrieval plan
        │
        ▼
Determine X,Y locations
        │
        ▼
Send commands to ESP32
        │
        ▼
Robot moves to cell
        │
        ▼
Retrieve required quantity
        │
        ▼
ESP32 confirms operation
        │
        ▼
Flask updates database
```

---

# 14. Flask Backend

Flask acts as the **central controller and decision-making layer**.

It manages:

### Inventory

* Products
* Boxes
* Quantities
* Locations
* Storage times

### Business rules

* 24-hour requirement
* FIFO ordering
* Quantity availability
* Cell capacity

### Robot control

* Movement commands
* Target coordinates
* Operation status
* Error handling
* ESP32 communication

### API

The frontend communicates with Flask through API endpoints.

Examples:

```text
GET  /api/products
GET  /api/inventory
GET  /api/cells

POST /api/products
POST /api/store

POST /api/retrieve/plan
POST /api/retrieve

GET  /api/robot/status
POST /api/robot/move
```

---

# 15. Web Interface

The frontend is built using:

```text
HTML
CSS
JavaScript
```

The UI should provide several major screens.

## Dashboard

Shows:

* Total products
* Total boxes
* Total inventory
* Ready inventory
* Waiting inventory
* Occupied cells
* Robot status
* Recent operations

---

## Store

Allows the operator to:

* See camera input
* See detected product
* See measured weight
* See calculated quantity
* Confirm the box
* See assigned cell
* Monitor robot movement

The process should be visually represented:

```text
✓ Product identified
✓ Weight measured
✓ Quantity calculated
✓ Cell selected
→ Robot moving
→ Box being stored
```

---

## Retrieve

Allows the operator to:

1. Select a product.
2. Enter requested quantity.
3. Check availability.
4. Display the FIFO retrieval plan.
5. Confirm the operation.

For example:

```text
Product A

Requested:
30

FIFO plan:

Box #101   X2,Y4   20 units   READY
Box #112   X4,Y1   10 units   READY

Total: 30
```

The operator then confirms the retrieval.

---

# 16. Inventory Visualization

The inventory page should display each box individually.

Example:

```text
┌──────┬─────────┬─────────┬──────────┬──────────────┐
│ Box  │ Product │ Cell    │ Quantity │ Status       │
├──────┼─────────┼─────────┼──────────┼──────────────┤
│ #101 │ A       │ X2,Y4   │ 20       │ READY        │
│ #105 │ A       │ X5,Y1   │ 15       │ READY        │
│ #108 │ B       │ X1,Y3   │ 10       │ WAITING      │
└──────┴─────────┴─────────┴──────────┴──────────────┘
```

For waiting boxes, the UI can display:

```text
WAITING
11h 32m remaining
```

This gives the operator immediate information about inventory availability.

---

# 17. Shelf Visualization

The UI should also provide a graphical representation of the physical shelf.

For example:

```text
                X →

          0      1      2      3      4

Y = 0    [ A ]  [ B ]  [   ]  [ A ]  [ C ]

Y = 1    [   ]  [ A ]  [ C ]  [ B ]  [   ]

Y = 2    [ B ]  [   ]  [ A ]  [ A ]  [ C ]
```

Clicking a cell could display:

```text
CELL X2,Y1

Capacity: 4

Box #101
Product A
Quantity: 20
Status: READY

Box #109
Product A
Quantity: 10
Status: WAITING
```

This gives the operator a direct visual connection between the **database and the physical shelf**.

---

# 18. ESP32 Controller

The ESP32 is responsible primarily for **physical control**, not inventory decisions.

It should handle:

* X-axis motor
* Y-axis motor
* Limit switches
* Position detection
* Box manipulation mechanism
* Sensors
* Load-cell interface if physically connected there
* Communication with Flask
* Reporting operation results

The ESP32 receives commands from Flask.

For example:

```text
MOVE X=3 Y=5
```

or:

```text
RETRIEVE BOX=105 QUANTITY=10
```

The ESP32 executes the physical operation and reports the result.

---

# 19. Separation of Responsibilities

A very important design principle is:

### Flask decides **WHAT should happen**

```text
Which product?
Which box?
How many?
Which cell?
What is the FIFO order?
Is the box ready?
```

### ESP32 decides **HOW to physically do it**

```text
Move motor
Read sensors
Stop at limit switch
Operate actuator
Report success/failure
```

This separation keeps the system easier to develop and troubleshoot.

---

# 20. Robot Confirmation

The final system should not update the database merely because Flask sent a command.

Instead:

```text
Flask
  │
  │ Retrieve Box #101
  ▼
ESP32
  │
  │ Execute
  ▼
XY Robot
  │
  │ Operation successful
  ▼
ESP32
  │
  │ SUCCESS
  ▼
Flask
  │
  ▼
Update database
```

If the robot fails:

```text
ESP32
   │
   ▼
ERROR
   │
   ▼
Flask
   │
   ├── Do NOT update inventory
   │
   └── Show error to operator
```

This prevents the database from becoming inconsistent with the physical shelf.

---

# 21. Complete System Workflow

Putting everything together:

```text
                    ┌───────────────┐
                    │ Incoming Box  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    Camera     │
                    └───────┬───────┘
                            │
                            ▼
                    Product Detection
                            │
                            ▼
                    ┌───────────────┐
                    │   Load Cell   │
                    └───────┬───────┘
                            │
                            ▼
                     Quantity Calc.
                            │
                            ▼
                    ┌───────────────┐
                    │ Flask Backend │
                    └───────┬───────┘
                            │
                    Find suitable Cell
                            │
                            ▼
                       X,Y Position
                            │
                            ▼
                         ESP32
                            │
                            ▼
                       XY Robot
                            │
                            ▼
                      Store Box
                            │
                            ▼
                    Database Record
                            │
                            ▼
                     Wait 24 Hours
                            │
                            ▼
                         READY
                            │
                            ▼
                  User requests product
                            │
                            ▼
                     FIFO Algorithm
                            │
                            ▼
                  Select oldest boxes
                            │
                            ▼
                       X,Y locations
                            │
                            ▼
                         ESP32
                            │
                            ▼
                       XY Robot
                            │
                            ▼
                     Retrieve Items
                            │
                            ▼
                   Confirm Operation
                            │
                            ▼
                    Update Database
```

# 22. Final System Concept

In one sentence, your project can be described as:

> **An automated FIFO inventory management system that uses product identification, weight-based quantity estimation, database tracking, and an ESP32-controlled XY robotic shelf to automatically store and retrieve product boxes while enforcing a minimum 24-hour storage period.**

The strongest part of your design is that you're not treating the shelf as simply a collection of quantities. You're tracking **individual physical boxes**, their **product**, **quantity**, **exact XY location**, and **storage timestamp**. That gives you the information necessary to implement reliable **FIFO + 24-hour eligibility** and to coordinate the digital inventory with the physical robot.
