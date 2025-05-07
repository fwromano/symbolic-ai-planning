(define (problem road-4)
    (:domain road)
    (:objects
        v1 - vehicle
        v2 - bulldozer
        l1 l2 l3 l4 l5 - location
    )
    (:init
        (at v1 l1)
        (at v2 l1)
        (rubble l2)
        (adjacent l1 l2)
        (adjacent l2 l1)
        (adjacent l2 l3)
        (adjacent l3 l2)
        (adjacent l3 l4)
        (adjacent l4 l3)
        (adjacent l4 l5)
        (adjacent l5 l4)
    )
    (:goal (at v1 l5))
)