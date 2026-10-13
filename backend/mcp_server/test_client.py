import asyncio
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
# MAIN
# ==================================================

async def main():

    print(
        "STARTING MCP CLIENT"
    )

    # ----------------------------------------------
    # MCP server parameters
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
    # Start MCP server
    # ----------------------------------------------

    async with stdio_client(
        server_params
    ) as (
        read_stream,
        write_stream,
    ):

        print(
            "SERVER PROCESS STARTED"
        )

        # ------------------------------------------
        # Create MCP session
        # ------------------------------------------

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            print(
                "INITIALIZING MCP SESSION"
            )

            await session.initialize()

            print(
                "MCP SESSION INITIALIZED"
            )

            # --------------------------------------
            # List tools
            # --------------------------------------

            tools = (
                await session.list_tools()
            )

            print(
                "\nMCP CONNECTION: SUCCESS"
            )

            print(
                "\nAvailable tools:"
            )

            for tool in tools.tools:

                print(
                    f"- {tool.name}"
                )

            # ======================================
            # GET USER
            # ======================================

            print(
                "\nCALLING get_user_tool..."
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

            print(
                "\nGET USER RESULT:"
            )

            print(
                user_result
            )

            # ======================================
            # GET CREDENTIAL
            # ======================================

            print(
                "\nCALLING get_credential_tool..."
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

            print(
                "\nGET CREDENTIAL RESULT:"
            )

            print(
                credential_result
            )

            # ======================================
            # CHECK CONSENT
            # ======================================

            print(
                "\nCALLING check_consent_tool..."
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

            print(
                "\nCHECK CONSENT RESULT:"
            )

            print(
                consent_result
            )

            # ======================================
            # VERIFY PQC
            # ======================================

            print(
                "\nCALLING verify_pqc_tool..."
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

            print(
                "\nVERIFY PQC RESULT:"
            )

            print(
                pqc_result
            )

            # ======================================
            # VERIFY CREDENTIAL
            # ======================================

            print(
                "\nCALLING verify_credential_tool..."
            )

            verification_result = (
                await session.call_tool(
                    "verify_credential_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print(
                "\nVERIFY CREDENTIAL RESULT:"
            )

            print(
                verification_result
            )

            # ======================================
            # CHECK REVOCATION
            # ======================================

            print(
                "\nCALLING check_revocation_tool..."
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

            print(
                "\nCHECK REVOCATION RESULT:"
            )

            print(
                revocation_result
            )

            # ======================================
            # VERIFY BLOCKCHAIN
            # ======================================

            print(
                "\nCALLING verify_blockchain_tool..."
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

            print(
                "\nVERIFY BLOCKCHAIN RESULT:"
            )

            print(
                blockchain_result
            )


                     # ======================================
            # GET VERIFICATION HISTORY
            # ======================================

            print(
                "\nCALLING get_verification_history_tool..."
            )

            verification_history_result = (
                await session.call_tool(
                    "get_verification_history_tool",
                    {
                        "credential_uuid":
                            TEST_CREDENTIAL_UUID
                    },
                )
            )

            print(
                "\nGET VERIFICATION HISTORY RESULT:"
            )

            print(
                verification_history_result
            )


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )