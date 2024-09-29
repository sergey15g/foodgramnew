from rest_framework.response import Response


class APIVersionMixin:
    def get_versioned_response(self, request):
        version = request.version
        version_data = {
            "1.0": {"version": "1.0", "message": "This is version 1.0"},
            "2.0": {"version": "2.0", "message": "This is version 2.0"}
        }
        data = version_data.get(version, {"error": "Unsupported version"})
        return Response(data)
