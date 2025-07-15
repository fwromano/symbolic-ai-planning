(define (domain exploration)
    (:requirements :strips :typing :equality :action-costs)
    
    (:types
        robot location - object
    )
    
    (:predicates
        (at ?r - robot ?l - location)
        (explored ?l - location)
        (adjacent ?l1 - location ?l2 - location)
        (can-traverse ?r - robot ?l - location)
        (can-observe ?r - robot ?l - location)
    )
    
    (:functions
        (total-cost)
        (traverse-cost ?r - robot ?l - location)
    )
    
    (:action move
        :parameters (?r - robot ?from - location ?to - location)
        :precondition (and
            (at ?r ?from)
            (adjacent ?from ?to)
            (can-traverse ?r ?to)
        )
        :effect (and
            (not (at ?r ?from))
            (at ?r ?to)
            (increase (total-cost) (traverse-cost ?r ?to))
        )
    )
    
    (:action observe
        :parameters (?r - robot ?l - location)
        :precondition (and
            (at ?r ?l)
            (can-observe ?r ?l)
        )
        :effect (explored ?l)
    )
)