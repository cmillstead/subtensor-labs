"""Tests for DelegationDetailSchema and enhanced SubnetPositionSchema fields."""

from engine.schemas.portfolio import (
    DelegationDetailSchema,
    SubnetPositionSchema,
)

HOTKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"


class TestDelegationDetailSchema:
    def test_valid_delegation(self) -> None:
        d = DelegationDetailSchema(
            validator_hotkey=HOTKEY,
            validator_name="Templar",
            delegated_amount=500.0,
            estimated_apy=8.2,
            take_rate=0.18,
        )
        assert d.validator_hotkey == HOTKEY
        assert d.validator_name == "Templar"
        assert d.delegated_amount == 500.0
        assert d.estimated_apy == 8.2
        assert d.take_rate == 0.18

    def test_optional_fields_default_to_none(self) -> None:
        d = DelegationDetailSchema(
            validator_hotkey=HOTKEY,
            delegated_amount=100.0,
            take_rate=0.1,
        )
        assert d.validator_name is None
        assert d.estimated_apy is None

    def test_json_serialization_roundtrip(self) -> None:
        d = DelegationDetailSchema(
            validator_hotkey=HOTKEY,
            validator_name="MyValidator",
            delegated_amount=250.0,
            estimated_apy=5.5,
            take_rate=0.12,
        )
        data = d.model_dump()
        assert data["validator_hotkey"] == HOTKEY
        assert data["validator_name"] == "MyValidator"
        restored = DelegationDetailSchema.model_validate(data)
        assert restored.estimated_apy == 5.5


class TestSubnetPositionSchemaNewFields:
    def test_new_fields_have_defaults(self) -> None:
        """subnet_name, alpha_holdings, delegations all have defaults."""
        pos = SubnetPositionSchema(
            netuid=3,
            hotkey=HOTKEY,
            staked_tao=100.0,
            alpha_value_tao=50.0,
            emission_share=0.05,
            incentive=0.0,
            trust=0.9,
            dividends=0.1,
            is_active=True,
            is_miner=False,
        )
        assert pos.subnet_name is None
        assert pos.alpha_holdings == 0.0
        assert pos.delegations == []

    def test_with_all_new_fields(self) -> None:
        delegation = DelegationDetailSchema(
            validator_hotkey=HOTKEY,
            delegated_amount=100.0,
            take_rate=0.1,
        )
        pos = SubnetPositionSchema(
            netuid=3,
            subnet_name="Templar",
            hotkey=HOTKEY,
            staked_tao=100.0,
            alpha_holdings=200.0,
            alpha_value_tao=50.0,
            emission_share=0.05,
            incentive=0.0,
            trust=0.9,
            dividends=0.1,
            is_active=True,
            is_miner=False,
            delegations=[delegation],
        )
        assert pos.subnet_name == "Templar"
        assert pos.alpha_holdings == 200.0
        assert len(pos.delegations) == 1
        assert pos.delegations[0].delegated_amount == 100.0

    def test_json_includes_new_fields(self) -> None:
        pos = SubnetPositionSchema(
            netuid=1,
            hotkey=HOTKEY,
            staked_tao=100.0,
            alpha_value_tao=50.0,
            emission_share=0.05,
            incentive=0.0,
            trust=0.9,
            dividends=0.1,
            is_active=True,
            is_miner=False,
        )
        data = pos.model_dump()
        assert "subnet_name" in data
        assert "alpha_holdings" in data
        assert "delegations" in data
        assert data["subnet_name"] is None
        assert data["alpha_holdings"] == 0.0
        assert data["delegations"] == []

    def test_serialization_roundtrip_with_delegations(self) -> None:
        delegation = DelegationDetailSchema(
            validator_hotkey=HOTKEY,
            validator_name="TestValidator",
            delegated_amount=500.0,
            estimated_apy=7.5,
            take_rate=0.15,
        )
        pos = SubnetPositionSchema(
            netuid=5,
            subnet_name="TestSubnet",
            hotkey=HOTKEY,
            staked_tao=500.0,
            alpha_holdings=1000.0,
            alpha_value_tao=250.0,
            emission_share=0.03,
            incentive=0.0,
            trust=0.8,
            dividends=0.2,
            is_active=True,
            is_miner=False,
            delegations=[delegation],
        )
        json_str = pos.model_dump_json()
        restored = SubnetPositionSchema.model_validate_json(json_str)
        assert restored.subnet_name == "TestSubnet"
        assert restored.alpha_holdings == 1000.0
        assert len(restored.delegations) == 1
        assert restored.delegations[0].validator_name == "TestValidator"
