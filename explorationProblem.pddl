(define (problem exploration-generated)
    (:domain exploration)
    
    (:objects
        B G - robot
        l11 l12 l13 l21 l22 l23 l31 l32 l33 - location
    )
    
    (:init
        ;; Robot starting positions
        (at B l11)
        (at G l11)

        ;; Traversability and costs
        (can-traverse B l11)
        (= (traverse-cost B l11) 1)
        (can-traverse G l11)
        (= (traverse-cost G l11) 1)
        (can-traverse B l12)
        (= (traverse-cost B l12) 1)
        (can-traverse B l13)
        (= (traverse-cost B l13) 1)
        (can-traverse G l13)
        (= (traverse-cost G l13) 1)
        (can-traverse B l21)
        (= (traverse-cost B l21) 1)
        (can-traverse G l21)
        (= (traverse-cost G l21) 1)
        (can-traverse B l22)
        (= (traverse-cost B l22) 5)
        (can-traverse G l22)
        (= (traverse-cost G l22) 5)
        (can-traverse B l23)
        (= (traverse-cost B l23) 1)
        (can-traverse G l23)
        (= (traverse-cost G l23) 1)
        (can-traverse B l31)
        (= (traverse-cost B l31) 1)
        (can-traverse G l31)
        (= (traverse-cost G l31) 1)
        (can-traverse B l32)
        (= (traverse-cost B l32) 1)
        (can-traverse G l32)
        (= (traverse-cost G l32) 1)
        (can-traverse B l33)
        (= (traverse-cost B l33) 1)
        (can-traverse G l33)
        (= (traverse-cost G l33) 1)

        ;; Observation capabilities
        (can-observe B l11)
        (can-observe G l11)
        (can-observe B l12)
        (can-observe G l12)
        (can-observe B l13)
        (can-observe G l13)
        (can-observe B l21)
        (can-observe G l21)
        (can-observe B l22)
        (can-observe G l22)
        (can-observe B l23)
        (can-observe G l23)
        (can-observe B l31)
        (can-observe G l31)
        (can-observe B l32)
        (can-observe G l32)
        (can-observe B l33)
        (can-observe G l33)

        ;; Grid adjacency
        (adjacent l11 l12) (adjacent l12 l11)
        (adjacent l11 l21) (adjacent l21 l11)
        (adjacent l12 l13) (adjacent l13 l12)
        (adjacent l12 l22) (adjacent l22 l12)
        (adjacent l13 l23) (adjacent l23 l13)
        (adjacent l21 l22) (adjacent l22 l21)
        (adjacent l21 l31) (adjacent l31 l21)
        (adjacent l22 l23) (adjacent l23 l22)
        (adjacent l22 l32) (adjacent l32 l22)
        (adjacent l23 l33) (adjacent l33 l23)
        (adjacent l31 l32) (adjacent l32 l31)
        (adjacent l32 l33) (adjacent l33 l32)

        (= (total-cost) 0)
    )
    
    (:goal (and
        ;; All locations explored
        (explored l11) (explored l12) (explored l13)
        (explored l21) (explored l22) (explored l23)
        (explored l31) (explored l32) (explored l33)
        ;; Robot goal positions
        (at B l33)
        (at G l33)
    ))
    
    (:metric minimize (total-cost))
)