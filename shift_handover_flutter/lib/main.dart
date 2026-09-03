import 'dart:async';
import 'package:flutter/material.dart';
import 'constants/theme_constants.dart';
import 'models/handover_models.dart';
import 'screens/login_screen.dart';
import 'services/api_service.dart';
import 'widgets/error_widget.dart';
import 'widgets/filter_panel.dart';
import 'widgets/handover_sections_widget.dart';
import 'widgets/header_bar.dart';
import 'widgets/loading_pipeline_widget.dart';
import 'widgets/pdf_actions_widget.dart';
import 'widgets/shift_config_widget.dart';
import 'widgets/source_status_widget.dart';

void main() {
  runApp(const ShiftHandoverApp());
}

class ShiftHandoverApp extends StatefulWidget {
  const ShiftHandoverApp({Key? key}) : super(key: key);

  @override
  State<ShiftHandoverApp> createState() => _ShiftHandoverAppState();
}

class _ShiftHandoverAppState extends State<ShiftHandoverApp> {
  Map<String, dynamic>? _currentUser = {
    "name": "Alex Rivera",
    "email": "operator@noc.internal",
    "role": "Lead On-Call SRE",
    "avatar": "AR",
  };

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SHIFT//HANDOVER',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: AppColors.background,
        primaryColor: AppColors.primaryAccent,
        cardColor: AppColors.card,
        colorScheme: const ColorScheme.dark(
          primary: AppColors.primaryAccent,
          secondary: AppColors.brightAccent,
          surface: AppColors.card,
          background: AppColors.background,
        ),
        dividerColor: AppColors.border,
      ),
      home: _currentUser == null
          ? LoginScreen(
              onLoginSuccess: (user) {
                setState(() => _currentUser = user);
              },
            )
          : DashboardScreen(
              currentUser: _currentUser,
              onLogout: () {
                setState(() => _currentUser = null);
              },
            ),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  final Map<String, dynamic>? currentUser;
  final VoidCallback? onLogout;

  const DashboardScreen({Key? key, this.currentUser, this.onLogout}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<SourceStatus> _sources = [];
  bool _isSourcesLoading = false;

  bool _isGenerating = false;
  int _pipelineStep = 0;
  Timer? _stepTimer;

  HandoverResponse? _handoverResponse;
  String? _errorMessage;

  FilterCriteria _filterCriteria = FilterCriteria();

  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _loadSources();
  }

  @override
  void dispose() {
    _stepTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadSources() async {
    setState(() => _isSourcesLoading = true);
    try {
      final statuses = await ApiService.fetchSourceStatus();
      if (mounted) {
        setState(() {
          _sources = statuses;
          _isSourcesLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSourcesLoading = false;
        });
      }
    }
  }

  void _startPipelineAnimation() {
    _pipelineStep = 0;
    _stepTimer?.cancel();
    _stepTimer = Timer.periodic(const Duration(milliseconds: 250), (timer) {
      if (_pipelineStep < 4) {
        setState(() => _pipelineStep++);
      } else {
        timer.cancel();
      }
    });
  }

  Future<void> _generateHandover(String shiftStart, String shiftEnd, bool dummy) async {
    setState(() {
      _isGenerating = true;
      _errorMessage = null;
      _pipelineStep = 0;
    });

    _startPipelineAnimation();

    try {
      final response = await ApiService.generateHandover(
        shiftStart: shiftStart,
        shiftEnd: shiftEnd,
        dummy: dummy,
      );

      // Allow brief animation to finish
      await Future.delayed(const Duration(milliseconds: 400));

      if (mounted) {
        setState(() {
          _handoverResponse = response;
          _isGenerating = false;
        });

        // Smooth scroll to results
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scrollController.hasClients) {
            _scrollController.animateTo(
              380,
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeOutCubic,
            );
          }
        });
      }
    } catch (e) {
      _stepTimer?.cancel();
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isGenerating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Header Bar with User Profile & Logout
          HeaderBar(
            onSettingsTap: _loadSources,
            currentUser: widget.currentUser,
            onLogout: widget.onLogout,
          ),

          // Main Scrollable Area
          Expanded(
            child: SingleChildScrollView(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Data Source Status Cards
                      SourceStatusWidget(
                        sources: _sources,
                        isLoading: _isSourcesLoading,
                        onRefresh: _loadSources,
                      ),
                      const SizedBox(height: 24),

                      // Shift Configuration & Generator Form
                      ShiftConfigWidget(
                        onGenerate: _generateHandover,
                        isLoading: _isGenerating,
                      ),
                      const SizedBox(height: 24),

                      // Loading Pipeline Step Indicator
                      if (_isGenerating) ...[
                        LoadingPipelineWidget(currentStep: _pipelineStep),
                        const SizedBox(height: 24),
                      ],

                      // Error Banner
                      if (_errorMessage != null) ...[
                        HandoverErrorWidget(
                          errorMessage: _errorMessage!,
                          onRetry: () => setState(() => _errorMessage = null),
                        ),
                        const SizedBox(height: 24),
                      ],

                      // Handover Results View
                      if (_handoverResponse != null && !_isGenerating) ...[
                        // Results Top Bar with PDF Actions
                        Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    "HANDOVER INTELLIGENCE REPORT",
                                    style: TextStyle(
                                      fontFamily: AppTypography.fontFamilyMono,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 16,
                                      color: AppColors.textMain,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    "Shift Window: ${_handoverResponse!.shiftWindow.start} → ${_handoverResponse!.shiftWindow.end}",
                                    style: const TextStyle(
                                      fontFamily: AppTypography.fontFamilyMono,
                                      fontSize: 11.5,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                              PdfActionsWidget(
                                pdfRelativeUrl: _handoverResponse!.pdfUrl,
                                pdfFilename: _handoverResponse!.pdfFilename,
                                shiftWindowLabel:
                                    "${_handoverResponse!.shiftWindow.start} → ${_handoverResponse!.shiftWindow.end}",
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 14),

                        // Search and Filter Panel
                        FilterPanel(
                          criteria: _filterCriteria,
                          onFiltersChanged: (newCriteria) {
                            setState(() => _filterCriteria = newCriteria);
                          },
                        ),
                        const SizedBox(height: 18),

                        // 4 Sections (Completed, In Progress, Blockers, Watch-list)
                        HandoverSectionsWidget(
                          response: _handoverResponse!,
                          filterCriteria: _filterCriteria,
                        ),
                        const SizedBox(height: 40),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
