(define (problem road-1)
    (:domain road)
    (:objects
        v1 - vehicle
        v2 - bulldozer
        l1 l2 - location
    )
    (:init
        (at v1 l1)
        (at v2 l1)
        (rubble l2)
        (adjacent l1 l2)
        (adjacent l2 l1)
    )
    (:goal (at v1 l2))
)