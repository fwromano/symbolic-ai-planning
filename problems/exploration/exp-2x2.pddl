(define (problem exp-2x2)
    (:domain exploration)

    (:objects
        B G - robot
        l11 l12 l21 l22 - location)
    (:init
        (at B l11)
    (at G l11)
    (adjacent l11 l21)
    (adjacent l11 l12)
    (adjacent l12 l22)
    (adjacent l21 l22)
    (adjacent l21 l11)
    (adjacent l12 l11)
    (adjacent l22 l12)
    (adjacent l22 l21)

    (can-traverse B l11)
    (can-traverse G l11)
    (can-observe G l11)

    (can-traverse B l12)
    (can-observe B l12)
    (can-traverse G l12)
    (can-observe G l12)

    (can-traverse B l21)
    (can-observe B l21)
    (can-observe G l21)
    
    (can-traverse B l22)
    (can-observe B l22)
    (can-traverse G l22)
    (can-observe G l22)

    (= (traverse-cost B l11) 1)
    (= (traverse-cost G l11) 1)
    (= (traverse-cost B l12) 1)
    (= (traverse-cost G l12) 1)
    (= (traverse-cost B l21) 1)
    (= (traverse-cost G l21) 1)
    (= (traverse-cost B l22) 5)
    (= (traverse-cost G l22) 5)
    (= (total-cost) 0))

    (:goal (and
        (explored l11)
(explored l12)
(explored l21)
(explored l22)
(at B l22)
(at G l22)))
    (:metric minimize (total-cost))
)