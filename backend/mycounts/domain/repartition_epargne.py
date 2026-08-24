"""Répartition exacte de l'épargne et désaffectation inverse déterministe.

Ce module ne crée aucune opération bancaire et n'appelle aucune IA. Il transforme une
décision déjà validée en centimes exacts, puis sait rétablir la couverture lorsque la
réserve réelle baisse. Tous les tris possèdent un dernier critère stable : l'UUID.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from uuid import UUID

from mycounts.domain.montants import Cents


class RepartitionInvalide(ValueError):
    """Une répartition violerait l'intégrité de la réserve ou d'une enveloppe."""


@dataclass(frozen=True)
class SouhaitAffectation:
    enveloppe_id: UUID
    poids: int
    """Poids relatif entier. Les pourcentages ne sont jamais une unité de stockage."""

    rang_priorite: int = 0
    """Le plus petit rang reçoit en premier les centimes restant après division."""

    maximum: Cents | None = None
    """Place restante dans l'enveloppe ; ``None`` signifie sans plafond validé."""

    def __post_init__(self) -> None:
        if self.poids < 0:
            raise RepartitionInvalide("Le poids d'une enveloppe ne peut pas être négatif.")
        if self.maximum is not None and self.maximum < 0:
            raise RepartitionInvalide("La place d'une enveloppe ne peut pas être négative.")


@dataclass(frozen=True)
class Affectation:
    enveloppe_id: UUID
    montant: Cents


def _verifier_identifiants_uniques(identifiants: Sequence[UUID]) -> None:
    if len(set(identifiants)) != len(identifiants):
        raise RepartitionInvalide("Une enveloppe ne peut apparaître qu'une fois.")


def repartir_exactement(
    montant: Cents, souhaits: Sequence[SouhaitAffectation]
) -> tuple[Affectation, ...]:
    """Ventile ``montant`` au prorata, puis attribue les restes par priorité et UUID.

    Les plafonds sont respectés et leur surplus est redistribué entre les enveloppes qui
    ont encore de la place. Le résultat contient aussi les enveloppes servies à zéro : son
    ordre stable facilite la persistance et rend deux exécutions byte-à-byte comparables.
    """

    if montant < 0:
        raise RepartitionInvalide("Le montant à affecter doit être positif ou nul.")
    _verifier_identifiants_uniques([souhait.enveloppe_id for souhait in souhaits])
    ordonnes = sorted(souhaits, key=lambda s: (s.rang_priorite, str(s.enveloppe_id)))
    allocations = {souhait.enveloppe_id: 0 for souhait in ordonnes}
    if montant == 0:
        return tuple(Affectation(s.enveloppe_id, Cents(0)) for s in ordonnes)

    actifs = [
        souhait
        for souhait in ordonnes
        if souhait.poids > 0 and (souhait.maximum is None or souhait.maximum > 0)
    ]
    if not actifs:
        raise RepartitionInvalide("Aucune enveloppe pondérée ne peut recevoir le montant.")
    capacite_bornee = sum(int(souhait.maximum) for souhait in actifs if souhait.maximum is not None)
    if all(souhait.maximum is not None for souhait in actifs) and capacite_bornee < montant:
        raise RepartitionInvalide("La place cumulée des enveloppes est insuffisante.")

    restant = int(montant)
    while restant > 0:
        poids_total = sum(souhait.poids for souhait in actifs)
        # Retirer d'abord les plafonds plus petits que leur quote-part, puis recalculer le
        # prorata. Affecter les autres quotes avant ce recalcul ferait dépendre le résultat
        # du nombre de plafonds rencontrés.
        satures: list[tuple[SouhaitAffectation, int]] = []
        for souhait in actifs:
            quote = restant * souhait.poids // poids_total
            if souhait.maximum is None:
                continue
            place = int(souhait.maximum) - allocations[souhait.enveloppe_id]
            if place <= quote:
                satures.append((souhait, place))
        if satures:
            for souhait, place in satures:
                allocations[souhait.enveloppe_id] += place
                restant -= place
            ids_satures = {souhait.enveloppe_id for souhait, _ in satures}
            actifs = [s for s in actifs if s.enveloppe_id not in ids_satures]
            if restant > 0 and not actifs:
                raise RepartitionInvalide("La place cumulée des enveloppes est insuffisante.")
            continue

        for souhait in actifs:
            quote = restant * souhait.poids // poids_total
            allocations[souhait.enveloppe_id] += quote
        distribue = sum(restant * souhait.poids // poids_total for souhait in actifs)
        restant -= distribue
        if restant == 0:
            break

        # Le reste d'une division proportionnelle est strictement inférieur au nombre
        # d'actifs. Un seul passage ordonné suffit, tout en respectant les plafonds.
        for souhait in actifs:
            if restant == 0:
                break
            maximum = souhait.maximum
            if maximum is not None and allocations[souhait.enveloppe_id] >= maximum:
                continue
            allocations[souhait.enveloppe_id] += 1
            restant -= 1
        if restant:
            raise RepartitionInvalide("Impossible d'attribuer tous les centimes.")

    return tuple(
        Affectation(souhait.enveloppe_id, Cents(allocations[souhait.enveloppe_id]))
        for souhait in ordonnes
    )


def valider_affectations_exactes(
    montant_confirme: Cents, affectations: Sequence[Affectation]
) -> None:
    """Barrière serveur entre une proposition (humaine ou IA) et le grand livre."""

    if montant_confirme < 0:
        raise RepartitionInvalide("Le virement confirmé doit être positif ou nul.")
    _verifier_identifiants_uniques([a.enveloppe_id for a in affectations])
    if any(affectation.montant < 0 for affectation in affectations):
        raise RepartitionInvalide("Une affectation ne peut pas être négative.")
    total = sum(int(affectation.montant) for affectation in affectations)
    if total != montant_confirme:
        raise RepartitionInvalide(
            "La somme des affectations doit égaler exactement le virement confirmé."
        )


@dataclass(frozen=True)
class EtatEnveloppe:
    enveloppe_id: UUID
    solde: Cents
    importance: int
    """Importance métier croissante : 1 est moins important que 5."""

    cible_couverture: Cents | None = None

    def __post_init__(self) -> None:
        if self.solde < 0:
            raise RepartitionInvalide("Le solde affecté d'une enveloppe ne peut être négatif.")
        if self.importance < 0:
            raise RepartitionInvalide("L'importance ne peut pas être négative.")
        if self.cible_couverture is not None and self.cible_couverture <= 0:
            raise RepartitionInvalide("Une cible de couverture doit être strictement positive.")


@dataclass(frozen=True)
class Desaffectation:
    enveloppe_id: UUID
    montant: Cents


def _cle_desaffectation(enveloppe: EtatEnveloppe) -> tuple[int, int, Fraction, str]:
    cible = enveloppe.cible_couverture
    # À importance égale, une couverture mesurable et forte peut céder avant une réserve
    # dont aucun niveau suffisant n'a encore été validé. Aucun taux n'est inventé.
    if cible is None:
        return enveloppe.importance, 1, Fraction(0, 1), str(enveloppe.enveloppe_id)
    couverture = Fraction(int(enveloppe.solde), int(cible))
    return enveloppe.importance, 0, -couverture, str(enveloppe.enveloppe_id)


def retablir_couverture(
    reserve_apres: Cents, enveloppes: Sequence[EtatEnveloppe]
) -> tuple[Desaffectation, ...]:
    """Ramène la somme affectée sous la réserve, selon l'ordre V1 déterministe."""

    if reserve_apres < 0:
        raise RepartitionInvalide("La réserve d'épargne réelle ne peut pas être négative.")
    _verifier_identifiants_uniques([e.enveloppe_id for e in enveloppes])
    total_affecte = sum(int(enveloppe.solde) for enveloppe in enveloppes)
    a_reprendre = max(0, total_affecte - int(reserve_apres))
    resultat: list[Desaffectation] = []
    for enveloppe in sorted(enveloppes, key=_cle_desaffectation):
        if a_reprendre == 0:
            break
        montant = min(a_reprendre, int(enveloppe.solde))
        if montant == 0:
            continue
        resultat.append(Desaffectation(enveloppe.enveloppe_id, Cents(montant)))
        a_reprendre -= montant
    if a_reprendre:
        raise RepartitionInvalide("La désaffectation calculée ne peut pas couvrir l'écart.")
    return tuple(resultat)


@dataclass(frozen=True)
class PlanRetrait:
    reserve_avant: Cents
    reserve_apres: Cents
    retrait: Cents
    non_affecte_consomme: Cents
    desaffectations: tuple[Desaffectation, ...]

    @property
    def total_explique(self) -> Cents:
        return Cents(
            int(self.non_affecte_consomme)
            + sum(int(ligne.montant) for ligne in self.desaffectations)
        )


def planifier_retrait(
    *,
    reserve_avant: Cents,
    retrait: Cents,
    enveloppes: Sequence[EtatEnveloppe],
) -> PlanRetrait:
    """Consomme le non-affecté puis désaffecte le reste, pour un retrait bancaire."""

    if reserve_avant < 0 or retrait < 0:
        raise RepartitionInvalide("La réserve et le retrait doivent être positifs ou nuls.")
    if retrait > reserve_avant:
        raise RepartitionInvalide("Un retrait ne peut pas dépasser la réserve constatée.")
    _verifier_identifiants_uniques([e.enveloppe_id for e in enveloppes])
    total_affecte = sum(int(enveloppe.solde) for enveloppe in enveloppes)
    if total_affecte > reserve_avant:
        raise RepartitionInvalide(
            "La réserve doit être couverte avant de planifier un retrait ordinaire."
        )
    non_affecte = int(reserve_avant) - total_affecte
    non_affecte_consomme = min(int(retrait), non_affecte)
    reserve_apres = Cents(int(reserve_avant) - int(retrait))
    desaffectations = retablir_couverture(reserve_apres, enveloppes)
    plan = PlanRetrait(
        reserve_avant=reserve_avant,
        reserve_apres=reserve_apres,
        retrait=retrait,
        non_affecte_consomme=Cents(non_affecte_consomme),
        desaffectations=desaffectations,
    )
    if plan.total_explique != retrait:
        raise AssertionError("Le plan de retrait doit expliquer chaque centime.")
    return plan
