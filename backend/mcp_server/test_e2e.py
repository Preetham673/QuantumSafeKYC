import asyncio
import json
import sys

from mcp import (
    ClientSession,
    StdioServerParameters,
)

from mcp.client.stdio import (
    stdio_client,
)


# ==================================================
# TEST DATA
# ==================================================

TEST_USER_UUID = (
    "f53bf005-7ab1-41e5-9dc7-388a4ffde14c"
)

TEST_CREDENTIAL_UUID = (
    "b7910bb9-c906-4195-8a99-72046142aaca"
)

TEST_VERIFIER_ID = (
    "TEST-VERIFIER"
)

TEST_PURPOSE = (
    "KYC Verification"
)


# ==================================================
# RESULT HELPER
# ==================================================

def print_result(
    name,
    result,
):
    print(
        f"\n{name}:"
    )

    print(
        result
    )


# ==================================================
# MAIN
# ==================================================

async def main():

    print(
        "=" * 60
    )

    print(
        "QUANTUMSAFEKYC MCP END-TO-END TEST"
    )

    print(
        "=" * 60
    )

    # ----------------------------------------------
    # MCP SERVER PARAMETERS
    # ----------------------------------------------

    server_params = (
        StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "mcp_server.server",
            ],
        )
    )

    # ----------------------------------------------
    # START MCP SERVER
    # ----------------------------------------------

    async with stdio_client(
        server_params
    ) as (
        read_stream,
        write_stream,
    ):

        print(
            "\n[1] MCP SERVER STARTED"
        )

        # ------------------------------------------
        # CREATE SESSION
        # ------------------------------------------

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print(
                "[2] MCP SESSION INITIALIZED"
            )

            # --------------------------------------
            # LIST TOOLS
            # --------------------------------------

            tools = (
                await session.list_tools()
            )

            print(
                "[3] MCP TOOLS DISCOVERED:",
                len(tools.tools),
            )

            for tool in tools.tools:

                print(
                    f"    - {tool.name}"
                )

            # ======================================
            # 1. GET USER
            # ======================================

            print(
                "\n[4] GET USER"
            )

            user_result = (
                await session.call_tool(
                    "get_user_tool",
                    {
                        "user_uuid":
                            TEST_USER_UUID
                    },
                )
            )

            print_result(
                "USER RESULT",
                user_result,
            )

            # ======================================
            # 2. GET CREDENTIAL
            # ======================================

            print(
                "\n[5] GET CREDENTIAL"
            )

            credential_result = (
                await session.call_tool(
                    "get_credential_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print_result(
                "CREDENTIAL RESULT",
                credential_result,
            )

            # ======================================
            # 3. CHECK CONSENT
            # ======================================

            print(
                "\n[6] CHECK CONSENT"
            )

            consent_result = (
                await session.call_tool(
                    "check_consent_tool",
                    {
                        "user_uuid":
                            TEST_USER_UUID,

                        "credential_uuid":
                            TEST_CREDENTIAL_UUID,

                        "verifier_id":
                            TEST_VERIFIER_ID,

                        "purpose":
                            TEST_PURPOSE,
                    },
                )
            )

            print_result(
                "CONSENT RESULT",
                consent_result,
            )

            # ======================================
            # 4. VERIFY PQC
            # ======================================

            print(
                "\n[7] VERIFY PQC"
            )

            pqc_result = (
                await session.call_tool(
                    "verify_pqc_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print_result(
                "PQC RESULT",
                pqc_result,
            )

            # ======================================
            # 5. VERIFY CREDENTIAL
            # ======================================

            print(
                "\n[8] VERIFY CREDENTIAL"
            )

            credential_verification_result = (
                await session.call_tool(
                    "verify_credential_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print_result(
                "CREDENTIAL VERIFICATION RESULT",
                credential_verification_result,
            )

            # ======================================
            # 6. CHECK REVOCATION
            # ======================================

            print(
                "\n[9] CHECK REVOCATION"
            )

            revocation_result = (
                await session.call_tool(
                    "check_revocation_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print_result(
                "REVOCATION RESULT",
                revocation_result,
            )

            # ======================================
            # 7. VERIFY BLOCKCHAIN
            # ======================================

            print(
                "\n[10] VERIFY BLOCKCHAIN"
            )

            blockchain_result = (
                await session.call_tool(
                    "verify_blockchain_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print_result(
                "BLOCKCHAIN RESULT",
                blockchain_result,
            )

            # ======================================
            # 8. VERIFICATION HISTORY
            # ======================================

            print(
                "\n[11] GET VERIFICATION HISTORY"
            )

            history_result = (
                await session.call_tool(
                    "get_verification_history_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print_result(
                "VERIFICATION HISTORY RESULT",
                history_result,
            )

            # ======================================
            # FINAL STATUS
            # ======================================

            print(
                "\n" + "=" * 60
            )

            print(
                "MCP END-TO-END TEST COMPLETED"
            )

            print(
                "=" * 60
            )

            print(
                "\nAll MCP workflow operations "
                "were executed successfully."
            )


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )