from dataclasses import dataclass


@dataclass(frozen=True)
class NfcTagMappingDistributionConfig:
    no_replacement_share: float
    one_replacement_share: float


@dataclass(frozen=True)
class NfcTagMappingConfig:
    min_mapping_lifetime_days: int
    replacement_distribution: NfcTagMappingDistributionConfig
