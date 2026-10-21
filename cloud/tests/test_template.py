import json
from pathlib import Path
from unittest import TestCase
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_template import build_template


class ProposedTemplateTests(TestCase):
    def setUp(self):
        self.template = json.loads(build_template())
        self.resources = self.template["Resources"]

    def test_table_is_bounded_on_demand_with_ttl_and_no_indexes_or_streams(self):
        properties = self.resources["GardenTable"]["Properties"]
        self.assertEqual(properties["BillingMode"], "PAY_PER_REQUEST")
        self.assertEqual(properties["OnDemandThroughput"], {"MaxReadRequestUnits": 5, "MaxWriteRequestUnits": 5})
        self.assertEqual(properties["TimeToLiveSpecification"], {"AttributeName": "expiresAt", "Enabled": True})
        self.assertNotIn("GlobalSecondaryIndexes", properties)
        self.assertNotIn("StreamSpecification", properties)

    def test_role_has_no_scan_or_wildcard_data_authority(self):
        statements = self.resources["FunctionRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
        self.assertEqual(set(statements[0]["Action"]), {"dynamodb:GetItem", "dynamodb:PutItem"})
        self.assertEqual(statements[0]["Resource"], {"Fn::GetAtt": ["GardenTable", "Arn"]})
        self.assertEqual(statements[1]["Resource"], {"Fn::GetAtt": ["FunctionLogs", "Arn"]})
        self.assertNotIn("*", json.dumps(statements))

    def test_api_uses_exact_origins_and_gateway2_with_small_throttles(self):
        cors = self.resources["GardenApi"]["Properties"]["CorsConfiguration"]
        self.assertEqual(cors["AllowOrigins"], {"Ref": "AllowedOrigins"})
        self.assertNotIn("*", self.template["Parameters"]["AllowedOrigins"]["Default"])
        self.assertNotIn("AllowCredentials", cors)
        self.assertEqual(self.resources["GardenIntegration"]["Properties"]["PayloadFormatVersion"], "2.0")
        settings = self.resources["GardenStage"]["Properties"]["DefaultRouteSettings"]
        self.assertEqual(settings["ThrottlingRateLimit"], 1)
        self.assertEqual(settings["ThrottlingBurstLimit"], 2)

    def test_function_has_no_vpc_layers_or_media_and_inline_code_matches_source(self):
        function = self.resources["GardenFunction"]["Properties"]
        self.assertEqual(function["MemorySize"], 128)
        self.assertEqual(function["Timeout"], 3)
        self.assertEqual(function["ReservedConcurrentExecutions"], 2)
        self.assertEqual(function["Code"]["ZipFile"], (Path(__file__).resolve().parents[1] / "garden_backup.py").read_text())
        self.assertEqual(function["Handler"], "index.lambda_handler")
        self.assertLessEqual(len(build_template().encode()), 51200)
        self.assertNotIn("VpcConfig", function)
        self.assertNotIn("Layers", function)
        self.assertNotIn("AccessLogSettings", self.resources["GardenStage"]["Properties"])
        self.assertNotIn("SSESpecification", self.resources["GardenTable"]["Properties"])

    def test_invoke_permission_is_scoped_to_one_account_api_and_garden_path(self):
        permission = self.resources["InvokePermission"]["Properties"]
        self.assertEqual(permission["SourceAccount"], {"Ref": "AWS::AccountId"})
        self.assertIn("${GardenApi}/*/*/gardens/*", permission["SourceArn"]["Fn::Sub"])
