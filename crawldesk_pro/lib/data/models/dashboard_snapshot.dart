import 'crawl_job.dart';
import 'dashboard_summary.dart';

class DashboardSnapshot {
  const DashboardSnapshot({
    required this.summary,
    required this.jobs,
  });

  final DashboardSummary summary;
  final List<CrawlJob> jobs;
}
